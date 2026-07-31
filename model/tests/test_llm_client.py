import json

import httpx
import pytest

from src.agents.llm_client import (
    GeminiJSONClient,
    LLMConfig,
    OpenAICompatibleClient,
)


def test_openai_compatible_client_parses_json():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/chat/completions"
        assert request.headers["Authorization"] == "Bearer test-key"

        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": (
                                '{"topic": "Gradient Descent", '
                                '"confidence": 0.9}'
                            )
                        }
                    }
                ]
            },
        )

    transport = httpx.MockTransport(handler)

    with httpx.Client(
        transport=transport,
        base_url="https://mock.example/v1",
    ) as http_client:
        client = OpenAICompatibleClient(
            config=LLMConfig(
                base_url="https://mock.example/v1",
                model="test-model",
                api_key="test-key",
            ),
            http_client=http_client,
        )

        result = client.chat_json(
            system_prompt="Return JSON.",
            user_prompt="Explain gradient descent.",
        )

    assert result["topic"] == "Gradient Descent"
    assert result["confidence"] == 0.9


def test_gemini_json_client_parses_json_and_skips_temperature_for_gemini_3():
    captured_payload = {}

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1beta/models/gemini-3.6-flash:generateContent"
        assert request.headers["x-goog-api-key"] == "test-key"
        captured_payload.update(json.loads(request.content))

        return httpx.Response(
            200,
            json={
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {
                                    "text": (
                                        '{"answer": "OK", '
                                        '"confidence": 0.9}'
                                    )
                                }
                            ]
                        }
                    }
                ]
            },
        )

    transport = httpx.MockTransport(handler)

    with httpx.Client(
        transport=transport,
        base_url="https://generativelanguage.googleapis.com/v1beta/",
    ) as http_client:
        client = GeminiJSONClient(
            config=LLMConfig(
                base_url="https://generativelanguage.googleapis.com/v1beta",
                model="gemini-3.6-flash",
                api_key="test-key",
            ),
            http_client=http_client,
        )

        result = client.chat_json(
            system_prompt="Return JSON.",
            user_prompt="Say OK.",
            temperature=0.2,
        )

    assert result["answer"] == "OK"
    assert result["confidence"] == 0.9
    assert "temperature" not in captured_payload["generationConfig"]
    assert captured_payload["generationConfig"]["maxOutputTokens"] == 1024


def test_gemini_json_client_does_not_retry_http_errors():
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(
            429,
            json={
                "error": {
                    "message": "Your prepayment credits are depleted."
                }
            },
        )

    transport = httpx.MockTransport(handler)

    with httpx.Client(
        transport=transport,
        base_url="https://generativelanguage.googleapis.com/v1beta/",
    ) as http_client:
        client = GeminiJSONClient(
            config=LLMConfig(
                base_url="https://generativelanguage.googleapis.com/v1beta",
                model="gemini-3.6-flash",
                api_key="test-key",
            ),
            http_client=http_client,
        )

        with pytest.raises(httpx.HTTPStatusError):
            client.chat_json(
                system_prompt="Return JSON.",
                user_prompt="Say OK.",
            )

    assert calls == 1
