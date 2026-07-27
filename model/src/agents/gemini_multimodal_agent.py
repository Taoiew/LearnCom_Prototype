import base64
import json
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType
from typing import Any, Self

import httpx

from schemas.vision_contract import VisionRequest
from src.agents.multimodal_client import (
    MultimodalConfigurationError,
    MultimodalImageError,
    MultimodalResponseError,
    MultimodalTransportError,
)


logger = logging.getLogger(__name__)


class GeminiMultimodalConfigurationError(
    MultimodalConfigurationError
):
    """Raised when Gemini Vision configuration is invalid."""


class GeminiMultimodalAuthenticationError(
    MultimodalTransportError
):
    """Raised when Gemini rejects credentials."""


class GeminiMultimodalRateLimitError(
    MultimodalTransportError
):
    """Raised when Gemini rate limits the request."""


class GeminiMultimodalProviderError(
    MultimodalTransportError
):
    """Raised when Gemini is unavailable or times out."""


class GeminiMultimodalResponseError(
    MultimodalResponseError
):
    """Raised when Gemini returns invalid structured output."""


def _compact_provider_message(value: Any) -> str:
    if isinstance(value, str):
        return " ".join(value.split())
    if isinstance(value, dict):
        message = value.get("message")
        if isinstance(message, str):
            return " ".join(message.split())
        return " ".join(
            json.dumps(value, ensure_ascii=False).split()
        )
    return ""


def _is_billing_credit_error(message: str) -> bool:
    normalized = message.lower()
    return (
        "prepayment credit" in normalized
        or "credits are depleted" in normalized
        or "billing" in normalized
    )


@dataclass(frozen=True)
class GeminiMultimodalConfig:
    base_url: str
    model: str
    api_key: str
    timeout_seconds: float = 90.0
    max_retries: int = 3
    temperature: float = 0.1
    max_output_tokens: int = 8192
    max_image_bytes: int = 10 * 1024 * 1024

    def __post_init__(self) -> None:
        if not self.base_url.strip():
            raise GeminiMultimodalConfigurationError(
                "GEMINI_API_BASE_URL must not be empty"
            )
        if not self.model.strip():
            raise GeminiMultimodalConfigurationError(
                "GEMINI_VISION_MODEL must not be empty"
            )
        if not self.api_key.strip():
            raise GeminiMultimodalConfigurationError(
                "GEMINI_API_KEY is required for Gemini Vision"
            )
        if self.timeout_seconds <= 0:
            raise GeminiMultimodalConfigurationError(
                "GEMINI_VISION_TIMEOUT_SECONDS must be greater than zero"
            )
        if self.max_retries < 0:
            raise GeminiMultimodalConfigurationError(
                "GEMINI_VISION_MAX_RETRIES must not be negative"
            )
        if not 0 <= self.temperature <= 2:
            raise GeminiMultimodalConfigurationError(
                "GEMINI_VISION_TEMPERATURE must be between 0 and 2"
            )
        if self.max_output_tokens <= 0:
            raise GeminiMultimodalConfigurationError(
                "GEMINI_VISION_MAX_OUTPUT_TOKENS must be greater than zero"
            )
        if self.max_image_bytes <= 0:
            raise GeminiMultimodalConfigurationError(
                "Gemini max_image_bytes must be greater than zero"
            )

    @classmethod
    def from_env(cls) -> "GeminiMultimodalConfig":
        return cls(
            base_url=os.getenv(
                "GEMINI_API_BASE_URL",
                "https://generativelanguage.googleapis.com/v1beta",
            ),
            model=os.getenv(
                "GEMINI_VISION_MODEL",
                "gemini-3.6-flash",
            ),
            api_key=os.getenv("GEMINI_API_KEY", ""),
            timeout_seconds=cls._read_float(
                "GEMINI_VISION_TIMEOUT_SECONDS",
                90.0,
            ),
            max_retries=cls._read_int(
                "GEMINI_VISION_MAX_RETRIES",
                3,
            ),
            temperature=cls._read_float(
                "GEMINI_VISION_TEMPERATURE",
                0.1,
            ),
            max_output_tokens=cls._read_int(
                "GEMINI_VISION_MAX_OUTPUT_TOKENS",
                8192,
            ),
        )

    @staticmethod
    def _read_float(name: str, default: float) -> float:
        raw_value = os.getenv(name)
        if raw_value is None:
            return default
        try:
            return float(raw_value)
        except ValueError as error:
            raise GeminiMultimodalConfigurationError(
                f"{name} must be a number"
            ) from error

    @staticmethod
    def _read_int(name: str, default: int) -> int:
        raw_value = os.getenv(name)
        if raw_value is None:
            return default
        try:
            return int(raw_value)
        except ValueError as error:
            raise GeminiMultimodalConfigurationError(
                f"{name} must be an integer"
            ) from error


class GeminiMultimodalClient:
    ALLOWED_MIME_TYPES = {"image/png", "image/jpeg"}
    RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
    AUTH_STATUS_CODES = {401, 403}

    def __init__(
        self,
        config: GeminiMultimodalConfig,
        http_client: httpx.Client | None = None,
    ) -> None:
        self.config = config
        self._owns_client = http_client is None
        self._headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": config.api_key,
        }
        self.http_client = http_client or httpx.Client(
            base_url=config.base_url.rstrip("/") + "/",
            headers=self._headers,
            timeout=config.timeout_seconds,
        )

    def chat_json(
        self,
        request: VisionRequest,
        system_prompt: str,
        temperature: float = 0.0,
    ) -> dict[str, Any]:
        image_bytes, detected_mime = self._load_and_validate_image(
            request
        )
        encoded_image = base64.b64encode(image_bytes).decode("ascii")

        prompt = self._build_user_prompt(
            request=request,
            system_prompt=system_prompt,
        )
        payload = self._build_payload(
            prompt=prompt,
            mime_type=detected_mime,
            encoded_image=encoded_image,
            temperature=(
                self.config.temperature
                if temperature == 0.0
                else temperature
            ),
        )

        started = time.monotonic()
        retry_count = 0

        response = self._post_with_retries(
            payload=payload,
            request=request,
        )
        try:
            parsed = self._parse_response(response)
        except GeminiMultimodalResponseError:
            repair_payload = self._build_payload(
                prompt=(
                    prompt
                    + "\n\nThe previous response was malformed. "
                    + "Return one valid JSON object only, with no Markdown."
                ),
                mime_type=detected_mime,
                encoded_image=encoded_image,
                temperature=0.0,
            )
            retry_count += 1
            response = self._post_with_retries(
                payload=repair_payload,
                request=request,
            )
            parsed = self._parse_response(response)

        duration_ms = int((time.monotonic() - started) * 1000)
        logger.info(
            "gemini_multimodal_request_completed",
            extra={
                "provider": "gemini",
                "model": self.config.model,
                "material_id": request.material_id,
                "request_id": request.request_id,
                "page_number": request.page_number,
                "duration_ms": duration_ms,
                "retry_count": retry_count,
                "response_status": response.status_code,
            },
        )

        return parsed

    def _post_with_retries(
        self,
        *,
        payload: dict[str, Any],
        request: VisionRequest,
    ) -> httpx.Response:
        attempts = self.config.max_retries + 1
        last_status: int | None = None

        for attempt_index in range(attempts):
            try:
                response = self.http_client.post(
                    f"models/{self.config.model}:generateContent",
                    headers=self._headers,
                    json=payload,
                )
            except httpx.TimeoutException as error:
                if attempt_index >= attempts - 1:
                    raise GeminiMultimodalProviderError(
                        "Gemini Vision request timed out"
                    ) from error
                self._sleep_before_retry(attempt_index)
                continue
            except httpx.TransportError as error:
                if attempt_index >= attempts - 1:
                    raise GeminiMultimodalProviderError(
                        "Gemini Vision request failed"
                    ) from error
                self._sleep_before_retry(attempt_index)
                continue

            last_status = response.status_code
            if 200 <= response.status_code < 300:
                if attempt_index:
                    logger.info(
                        "gemini_multimodal_request_recovered",
                        extra={
                            "provider": "gemini",
                            "model": self.config.model,
                            "material_id": request.material_id,
                            "request_id": request.request_id,
                            "page_number": request.page_number,
                            "retry_count": attempt_index,
                            "response_status": response.status_code,
                        },
                    )
                return response

            if response.status_code in self.AUTH_STATUS_CODES:
                raise GeminiMultimodalAuthenticationError(
                    self._provider_error_message(
                        response,
                        fallback=(
                            "Gemini Vision authentication failed"
                        ),
                    )
                )

            if response.status_code == 429:
                if attempt_index >= attempts - 1:
                    provider_message = self._provider_error_message(
                        response,
                        fallback=(
                            "Gemini Vision rate limit exceeded"
                        ),
                    )
                    if _is_billing_credit_error(provider_message):
                        raise GeminiMultimodalProviderError(
                            provider_message.replace(
                                "Gemini Vision rate limit exceeded",
                                "Gemini Vision billing credits are depleted",
                                1,
                            )
                        )
                    raise GeminiMultimodalRateLimitError(
                        provider_message
                    )
                self._sleep_before_retry(attempt_index)
                continue

            if response.status_code in self.RETRYABLE_STATUS_CODES:
                if attempt_index >= attempts - 1:
                    raise GeminiMultimodalProviderError(
                        self._provider_error_message(
                            response,
                            fallback=(
                                "Gemini Vision provider unavailable"
                            ),
                        )
                    )
                self._sleep_before_retry(attempt_index)
                continue

            raise GeminiMultimodalProviderError(
                self._provider_error_message(
                    response,
                    fallback="Gemini Vision request was rejected",
                )
            )

        raise GeminiMultimodalProviderError(
            "Gemini Vision request failed"
            + (f" with status {last_status}" if last_status else "")
        )

    def _build_payload(
        self,
        *,
        prompt: str,
        mime_type: str,
        encoded_image: str,
        temperature: float,
    ) -> dict[str, Any]:
        generation_config: dict[str, Any] = {
            "maxOutputTokens": self.config.max_output_tokens,
            "response_mime_type": "application/json",
            "response_schema": self._response_schema(),
        }
        if not self._uses_deprecated_sampling_parameters():
            generation_config["temperature"] = temperature

        return {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {"text": prompt},
                        {
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": encoded_image,
                            }
                        },
                    ],
                }
            ],
            "generationConfig": generation_config,
        }

    def _uses_deprecated_sampling_parameters(self) -> bool:
        model = self.config.model.lower()
        return (
            model.startswith("gemini-3.")
            or model.startswith("gemini-flash-latest")
            or model.startswith("gemini-pro-latest")
        )

    @staticmethod
    def _build_user_prompt(
        *,
        request: VisionRequest,
        system_prompt: str,
    ) -> str:
        metadata = {
            "request_id": request.request_id,
            "material_id": request.material_id,
            "material_name": request.material_name,
            "page_number": request.page_number,
            "asset_id": request.asset_id,
            "image_width_pixels": request.image_width_pixels,
            "image_height_pixels": request.image_height_pixels,
            "extracted_text": request.extracted_text,
            "tasks": [task.value for task in request.tasks],
            "prompt_version": request.prompt_version,
        }
        return (
            system_prompt
            + "\n\nVision request metadata:\n"
            + json.dumps(metadata, ensure_ascii=False)
        )

    @classmethod
    def _parse_response(
        cls,
        response: httpx.Response,
    ) -> dict[str, Any]:
        try:
            body = response.json()
            text_parts = []
            candidates = body.get("candidates")
            if not isinstance(candidates, list) or not candidates:
                raise GeminiMultimodalResponseError(
                    cls._empty_candidates_message(body)
                )
            first_candidate = candidates[0]
            if not isinstance(first_candidate, dict):
                raise TypeError("Gemini candidate must be an object")
            content_body = first_candidate.get("content")
            if not isinstance(content_body, dict):
                raise GeminiMultimodalResponseError(
                    cls._missing_content_message(first_candidate)
                )
            parts = content_body.get("parts")
            if not isinstance(parts, list):
                raise TypeError("Gemini content parts must be an array")

            for part in parts:
                if not isinstance(part, dict):
                    continue
                text = part.get("text")
                if isinstance(text, str):
                    text_parts.append(text)
            content = "\n".join(text_parts).strip()
            if not content:
                raise GeminiMultimodalResponseError(
                    cls._missing_text_message(first_candidate)
                )
            parsed = json.loads(content)
            if not isinstance(parsed, dict):
                raise TypeError("Gemini content must be a JSON object")
            return parsed
        except (
            KeyError,
            IndexError,
            TypeError,
            json.JSONDecodeError,
        ) as error:
            raise GeminiMultimodalResponseError(
                "Gemini Vision response is not valid structured JSON"
            ) from error

    @staticmethod
    def _provider_error_message(
        response: httpx.Response,
        *,
        fallback: str,
    ) -> str:
        details: list[str] = []
        try:
            body = response.json()
        except json.JSONDecodeError:
            body = None

        if isinstance(body, dict):
            error = body.get("error")
            provider_message = _compact_provider_message(error)
            if provider_message:
                details.append(provider_message)
        else:
            raw_text = " ".join(response.text.split())
            if raw_text:
                details.append(raw_text[:300])

        message = (
            f"{fallback} with HTTP status {response.status_code}"
        )
        if details:
            message += f": {details[0]}"
        return message

    @staticmethod
    def _empty_candidates_message(
        body: dict[str, Any],
    ) -> str:
        prompt_feedback = body.get("promptFeedback")
        detail = _compact_provider_message(prompt_feedback)
        if detail:
            return (
                "Gemini Vision response did not include candidates: "
                f"{detail}"
            )
        return "Gemini Vision response did not include candidates"

    @staticmethod
    def _missing_content_message(
        candidate: dict[str, Any],
    ) -> str:
        finish_reason = candidate.get("finishReason")
        if isinstance(finish_reason, str) and finish_reason:
            return (
                "Gemini Vision candidate did not include content "
                f"(finishReason={finish_reason})"
            )
        return "Gemini Vision candidate did not include content"

    @staticmethod
    def _missing_text_message(
        candidate: dict[str, Any],
    ) -> str:
        finish_reason = candidate.get("finishReason")
        if isinstance(finish_reason, str) and finish_reason:
            return (
                "Gemini Vision candidate did not include text "
                f"(finishReason={finish_reason})"
            )
        return "Gemini Vision candidate did not include text"

    def _load_and_validate_image(
        self,
        request: VisionRequest,
    ) -> tuple[bytes, str]:
        image_path = Path(request.image_path)
        if not image_path.is_file():
            raise MultimodalImageError(
                f"Image file not found: {image_path}"
            )
        file_size = image_path.stat().st_size
        if file_size <= 0:
            raise MultimodalImageError("Image file must not be empty")
        if file_size > self.config.max_image_bytes:
            raise MultimodalImageError(
                "Image exceeds configured size limit"
            )
        image_bytes = image_path.read_bytes()
        detected_mime = self._detect_mime_type(image_bytes)
        if detected_mime not in self.ALLOWED_MIME_TYPES:
            raise MultimodalImageError(
                "Unsupported image MIME type"
            )
        if request.mime_type != detected_mime:
            raise MultimodalImageError(
                "Declared image MIME type does not match file content"
            )
        return image_bytes, detected_mime

    @staticmethod
    def _detect_mime_type(image_bytes: bytes) -> str:
        if image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
            return "image/png"
        if image_bytes.startswith(b"\xff\xd8\xff"):
            return "image/jpeg"
        return "application/octet-stream"

    @staticmethod
    def _response_schema() -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["success", "partial", "needs_review", "failed"],
                },
                "page_summary": {"type": "string"},
                "ocr_text": {"type": "string"},
                "visual_elements": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "element_id": {"type": "string"},
                            "element_type": {
                                "type": "string",
                                "enum": [
                                    "image",
                                    "diagram",
                                    "chart",
                                    "table",
                                    "equation",
                                    "code_block",
                                    "other",
                                ],
                            },
                            "title": {"type": "string"},
                            "description": {"type": "string"},
                            "extracted_text": {"type": "string"},
                            "bounding_box": {
                                "type": "array",
                                "items": {"type": "number"},
                                "nullable": True,
                            },
                            "confidence": {"type": "number"},
                        },
                        "required": [
                            "element_id",
                            "element_type",
                            "description",
                            "confidence",
                        ],
                    },
                },
                "tables": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "table_id": {"type": "string"},
                            "title": {"type": "string"},
                            "headers": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "rows": {
                                "type": "array",
                                "items": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                            },
                            "notes": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "bounding_box": {
                                "type": "array",
                                "items": {"type": "number"},
                                "nullable": True,
                            },
                            "confidence": {"type": "number"},
                        },
                        "required": [
                            "table_id",
                            "headers",
                            "rows",
                            "confidence",
                        ],
                    },
                },
                "relationships": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "source_element_id": {"type": "string"},
                            "target_element_id": {"type": "string"},
                            "relation": {"type": "string"},
                            "confidence": {"type": "number"},
                        },
                        "required": [
                            "source_element_id",
                            "target_element_id",
                            "relation",
                            "confidence",
                        ],
                    },
                },
                "warnings": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "confidence": {"type": "number"},
            },
            "required": [
                "status",
                "page_summary",
                "ocr_text",
                "visual_elements",
                "tables",
                "relationships",
                "warnings",
                "confidence",
            ],
        }

    @staticmethod
    def _sleep_before_retry(attempt_index: int) -> None:
        time.sleep(min(0.5 * (2**attempt_index), 4.0))

    def close(self) -> None:
        if self._owns_client:
            self.http_client.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()
