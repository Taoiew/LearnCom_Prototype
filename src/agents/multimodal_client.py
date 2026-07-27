import base64
import json
import os
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType
from typing import Any, Self

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from schemas.vision_contract import VisionRequest


class MultimodalClientError(RuntimeError):
    """Base error for external multimodal operations."""


class MultimodalConfigurationError(
    MultimodalClientError
):
    """Raised when multimodal configuration is invalid."""


class MultimodalImageError(MultimodalClientError):
    """Raised when an input image is missing or invalid."""


class MultimodalTransportError(
    MultimodalClientError
):
    """Raised when the external provider cannot be reached."""


class MultimodalResponseError(
    MultimodalClientError
):
    """Raised when the provider returns an invalid response."""


@dataclass(frozen=True)
class MultimodalConfig:
    base_url: str
    model: str
    api_key: str = ""
    timeout_seconds: float = 60.0
    max_image_bytes: int = 10 * 1024 * 1024

    def __post_init__(self) -> None:
        if not self.base_url.strip():
            raise MultimodalConfigurationError(
                "Multimodal base_url must not be empty"
            )

        if not self.model.strip():
            raise MultimodalConfigurationError(
                "Multimodal model must not be empty"
            )

        if self.timeout_seconds <= 0:
            raise MultimodalConfigurationError(
                "timeout_seconds must be greater than zero"
            )

        if self.max_image_bytes <= 0:
            raise MultimodalConfigurationError(
                "max_image_bytes must be greater than zero"
            )

    @classmethod
    def from_env(cls) -> "MultimodalConfig":
        return cls(
            base_url=os.getenv(
                "EXTERNAL_MULTIMODAL_BASE_URL",
                "",
            ),
            model=os.getenv(
                "EXTERNAL_MULTIMODAL_MODEL",
                "",
            ),
            api_key=os.getenv(
                "EXTERNAL_MULTIMODAL_API_KEY",
                "",
            ),
            timeout_seconds=cls._read_float(
                name=(
                    "EXTERNAL_MULTIMODAL_TIMEOUT_SECONDS"
                ),
                default=60.0,
            ),
            max_image_bytes=cls._read_int(
                name=(
                    "EXTERNAL_MULTIMODAL_MAX_IMAGE_BYTES"
                ),
                default=10 * 1024 * 1024,
            ),
        )

    @staticmethod
    def _read_float(
        name: str,
        default: float,
    ) -> float:
        raw_value = os.getenv(name)

        if raw_value is None:
            return default

        try:
            return float(raw_value)
        except ValueError as error:
            raise MultimodalConfigurationError(
                f"{name} must be a number"
            ) from error

    @staticmethod
    def _read_int(
        name: str,
        default: int,
    ) -> int:
        raw_value = os.getenv(name)

        if raw_value is None:
            return default

        try:
            return int(raw_value)
        except ValueError as error:
            raise MultimodalConfigurationError(
                f"{name} must be an integer"
            ) from error


class OpenAICompatibleMultimodalClient:
    ALLOWED_MIME_TYPES = {
        "image/png",
        "image/jpeg",
        "image/webp",
    }

    def __init__(
        self,
        config: MultimodalConfig,
        http_client: httpx.Client | None = None,
    ) -> None:
        self.config = config
        self._owns_client = http_client is None

        self._headers = {
            "Content-Type": "application/json",
        }

        if config.api_key:
            self._headers["Authorization"] = (
                f"Bearer {config.api_key}"
            )

        self.http_client = http_client or httpx.Client(
            base_url=(
                config.base_url.rstrip("/") + "/"
            ),
            headers=self._headers,
            timeout=config.timeout_seconds,
        )

    def chat_json(
        self,
        request: VisionRequest,
        system_prompt: str,
        temperature: float = 0.0,
    ) -> dict[str, Any]:
        image_bytes, detected_mime = (
            self._load_and_validate_image(request)
        )

        encoded_image = base64.b64encode(
            image_bytes
        ).decode("ascii")

        data_url = (
            f"data:{detected_mime};base64,"
            f"{encoded_image}"
        )

        metadata = {
            "request_id": request.request_id,
            "material_id": request.material_id,
            "material_name": request.material_name,
            "page_number": request.page_number,
            "asset_id": request.asset_id,
            "extracted_text": request.extracted_text,
            "tasks": [
                task.value
                for task in request.tasks
            ],
            "prompt_version": request.prompt_version,
        }

        payload = {
            "model": self.config.model,
            "temperature": temperature,
            "response_format": {
                "type": "json_object",
            },
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(
                                metadata,
                                ensure_ascii=False,
                            ),
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": data_url,
                                "detail": "high",
                            },
                        },
                    ],
                },
            ],
        }

        try:
            response = self._post(payload)
        except (
            httpx.TransportError,
            httpx.HTTPStatusError,
        ) as error:
            raise MultimodalTransportError(
                "External multimodal request failed"
            ) from error

        return self._parse_response(response)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(
            multiplier=0.5,
            min=0.5,
            max=4,
        ),
        retry=retry_if_exception_type(
            (
                httpx.TransportError,
                httpx.HTTPStatusError,
            )
        ),
        reraise=True,
    )
    def _post(
        self,
        payload: dict[str, Any],
    ) -> httpx.Response:
        response = self.http_client.post(
            "chat/completions",
            headers=self._headers,
            json=payload,
        )
        response.raise_for_status()
        return response

    @staticmethod
    def _parse_response(
        response: httpx.Response,
    ) -> dict[str, Any]:
        try:
            response_body = response.json()
            content = response_body[
                "choices"
            ][0]["message"]["content"]

            if not isinstance(content, str):
                raise TypeError(
                    "Multimodal content must be a string"
                )

            parsed_content = json.loads(content)

            if not isinstance(parsed_content, dict):
                raise TypeError(
                    "Multimodal content must be "
                    "a JSON object"
                )

            return parsed_content

        except (
            KeyError,
            IndexError,
            TypeError,
            json.JSONDecodeError,
        ) as error:
            raise MultimodalResponseError(
                "Multimodal response is not valid "
                "structured JSON"
            ) from error

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
            raise MultimodalImageError(
                "Image file must not be empty"
            )

        if file_size > self.config.max_image_bytes:
            raise MultimodalImageError(
                "Image exceeds configured size limit"
            )

        image_bytes = image_path.read_bytes()
        detected_mime = self._detect_mime_type(
            image_bytes
        )

        if detected_mime not in self.ALLOWED_MIME_TYPES:
            raise MultimodalImageError(
                "Unsupported image MIME type"
            )

        if request.mime_type != detected_mime:
            raise MultimodalImageError(
                "Declared image MIME type does not "
                "match file content"
            )

        return image_bytes, detected_mime

    @staticmethod
    def _detect_mime_type(
        image_bytes: bytes,
    ) -> str:
        if image_bytes.startswith(
            b"\x89PNG\r\n\x1a\n"
        ):
            return "image/png"

        if image_bytes.startswith(b"\xff\xd8\xff"):
            return "image/jpeg"

        if (
            len(image_bytes) >= 12
            and image_bytes[:4] == b"RIFF"
            and image_bytes[8:12] == b"WEBP"
        ):
            return "image/webp"

        return "application/octet-stream"

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