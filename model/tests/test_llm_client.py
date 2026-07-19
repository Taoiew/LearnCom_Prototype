import httpx

from src.agents.llm_client import (
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