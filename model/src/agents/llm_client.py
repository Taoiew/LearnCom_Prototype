import json
from dataclasses import dataclass
from types import TracebackType
from typing import Any, Self

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)


class LLMClientError(RuntimeError):
    """Raised when the LLM response does not match the expected format."""


@dataclass(frozen=True)
class LLMConfig:
    base_url: str
    model: str
    api_key: str = ""
    timeout_seconds: float = 60.0


class OpenAICompatibleClient:
    def __init__(
        self,
        config: LLMConfig,
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
            base_url=config.base_url.rstrip("/"),
            headers=self._headers,
            timeout=config.timeout_seconds,
        )

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
    def chat_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
    ) -> dict[str, Any]:
        response = self.http_client.post(
            "/chat/completions",
            headers=self._headers,
            json={
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
                        "content": user_prompt,
                    },
                ],
            },
        )

        response.raise_for_status()

        try:
            response_body = response.json()
            content = response_body["choices"][0]["message"]["content"]

            if not isinstance(content, str):
                raise TypeError("LLM content must be a string")

            parsed_content = json.loads(content)

            if not isinstance(parsed_content, dict):
                raise TypeError("LLM content must be a JSON object")

            return parsed_content

        except (
            KeyError,
            IndexError,
            TypeError,
            json.JSONDecodeError,
        ) as error:
            raise LLMClientError(
                "LLM response is not valid structured JSON"
            ) from error

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