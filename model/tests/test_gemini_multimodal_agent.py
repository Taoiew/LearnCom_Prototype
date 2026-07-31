import json
from pathlib import Path

import httpx
import pytest

from schemas.vision_contract import VisionRequest
from src.agents.gemini_multimodal_agent import (
    GeminiMultimodalAuthenticationError,
    GeminiMultimodalClient,
    GeminiMultimodalConfig,
    GeminiMultimodalProviderError,
    GeminiMultimodalResponseError,
)


def create_config(
    *,
    max_retries: int = 0,
    model: str = "gemini-test-model",
) -> GeminiMultimodalConfig:
    return GeminiMultimodalConfig(
        base_url="https://generativelanguage.googleapis.com/v1beta",
        model=model,
        api_key="secret-test-key",
        timeout_seconds=1,
        max_retries=max_retries,
        temperature=0.1,
        max_output_tokens=1024,
    )


def create_request(
    image_path: Path,
    *,
    mime_type: str = "image/png",
) -> VisionRequest:
    return VisionRequest(
        request_id="vision-request-001",
        material_id="material-001",
        material_name="lesson.pdf",
        page_number=3,
        asset_id="asset-page-003",
        image_path=str(image_path),
        mime_type=mime_type,
        image_width_pixels=10,
        image_height_pixels=10,
        extracted_text="Known text layer",
    )


def valid_payload() -> dict:
    return {
        "status": "success",
        "page_summary": "The page shows a labeled diagram.",
        "ocr_text": "Diagram A",
        "visual_elements": [
            {
                "element_id": "element-001",
                "element_type": "diagram",
                "title": "Diagram A",
                "description": "A visible diagram with one label.",
                "extracted_text": "Diagram A",
                "bounding_box": None,
                "confidence": 0.92,
            }
        ],
        "tables": [],
        "relationships": [],
        "warnings": [],
        "confidence": 0.92,
    }


def gemini_response(payload: dict | str) -> httpx.Response:
    text = payload if isinstance(payload, str) else json.dumps(payload)
    return httpx.Response(
        200,
        json={
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": text,
                            }
                        ]
                    }
                }
            ]
        },
    )


def write_png(path: Path) -> None:
    path.write_bytes(b"\x89PNG\r\n\x1a\nimage")


def write_jpeg(path: Path) -> None:
    path.write_bytes(b"\xff\xd8\xffimage")


def test_valid_png_request_returns_parsed_structured_response(
    tmp_path: Path,
) -> None:
    image_path = tmp_path / "page.png"
    write_png(image_path)

    client = GeminiMultimodalClient(
        config=create_config(),
        http_client=httpx.Client(
            transport=httpx.MockTransport(
                lambda request: gemini_response(valid_payload())
            ),
            base_url="https://generativelanguage.googleapis.com/v1beta/",
        ),
    )

    result = client.chat_json(
        request=create_request(image_path),
        system_prompt="Return JSON.",
    )

    assert result["status"] == "success"
    assert result["visual_elements"][0]["element_type"] == "diagram"


def test_valid_jpeg_request_returns_parsed_structured_response(
    tmp_path: Path,
) -> None:
    image_path = tmp_path / "photo.jpeg"
    write_jpeg(image_path)

    client = GeminiMultimodalClient(
        config=create_config(),
        http_client=httpx.Client(
            transport=httpx.MockTransport(
                lambda request: gemini_response(valid_payload())
            ),
            base_url="https://generativelanguage.googleapis.com/v1beta/",
        ),
    )

    result = client.chat_json(
        request=create_request(image_path, mime_type="image/jpeg"),
        system_prompt="Return JSON.",
    )

    assert result["confidence"] == 0.92


def test_rendered_pdf_page_request_uses_png_inline_data(
    tmp_path: Path,
) -> None:
    image_path = tmp_path / "rendered-page.png"
    write_png(image_path)
    seen_payload: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen_payload.update(json.loads(request.content))
        return gemini_response(valid_payload())

    client = GeminiMultimodalClient(
        config=create_config(),
        http_client=httpx.Client(
            transport=httpx.MockTransport(handler),
            base_url="https://generativelanguage.googleapis.com/v1beta/",
        ),
    )

    client.chat_json(
        request=create_request(image_path),
        system_prompt="Return JSON.",
    )

    inline_data = seen_payload["contents"][0]["parts"][1]["inline_data"]
    assert inline_data["mime_type"] == "image/png"
    assert inline_data["data"]


def test_correct_gemini_endpoint_model_and_json_config_are_used(
    tmp_path: Path,
) -> None:
    image_path = tmp_path / "page.png"
    write_png(image_path)

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == (
            "/v1beta/models/gemini-test-model:generateContent"
        )
        assert request.headers["x-goog-api-key"] == "secret-test-key"
        payload = json.loads(request.content)
        assert payload["generationConfig"]["response_mime_type"] == (
            "application/json"
        )
        assert payload["generationConfig"]["response_schema"]["type"] == (
            "object"
        )
        return gemini_response(valid_payload())

    client = GeminiMultimodalClient(
        config=create_config(),
        http_client=httpx.Client(
            transport=httpx.MockTransport(handler),
            base_url="https://generativelanguage.googleapis.com/v1beta/",
        ),
    )

    client.chat_json(
        request=create_request(image_path),
        system_prompt="Return JSON.",
    )


def test_gemini_3_models_omit_deprecated_temperature(
    tmp_path: Path,
) -> None:
    image_path = tmp_path / "page.png"
    write_png(image_path)

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == (
            "/v1beta/models/gemini-3.6-flash:generateContent"
        )
        payload = json.loads(request.content)
        assert "temperature" not in payload["generationConfig"]
        assert payload["generationConfig"]["maxOutputTokens"] == 1024
        return gemini_response(valid_payload())

    client = GeminiMultimodalClient(
        config=create_config(model="gemini-3.6-flash"),
        http_client=httpx.Client(
            transport=httpx.MockTransport(handler),
            base_url="https://generativelanguage.googleapis.com/v1beta/",
        ),
    )

    client.chat_json(
        request=create_request(image_path),
        system_prompt="Return JSON.",
    )


def test_malformed_json_raises_controlled_provider_error(
    tmp_path: Path,
) -> None:
    image_path = tmp_path / "page.png"
    write_png(image_path)

    client = GeminiMultimodalClient(
        config=create_config(),
        http_client=httpx.Client(
            transport=httpx.MockTransport(
                lambda request: gemini_response("not-json")
            ),
            base_url="https://generativelanguage.googleapis.com/v1beta/",
        ),
    )

    with pytest.raises(
        GeminiMultimodalResponseError,
        match="not valid structured JSON",
    ):
        client.chat_json(
            request=create_request(image_path),
            system_prompt="Return JSON.",
        )


def test_missing_candidates_reports_gemini_response_shape(
    tmp_path: Path,
) -> None:
    image_path = tmp_path / "page.png"
    write_png(image_path)

    client = GeminiMultimodalClient(
        config=create_config(),
        http_client=httpx.Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(
                    200,
                    json={
                        "promptFeedback": {
                            "blockReason": "OTHER",
                        }
                    },
                )
            ),
            base_url="https://generativelanguage.googleapis.com/v1beta/",
        ),
    )

    with pytest.raises(
        GeminiMultimodalResponseError,
        match="did not include candidates",
    ):
        client.chat_json(
            request=create_request(image_path),
            system_prompt="Return JSON.",
        )


@pytest.mark.parametrize("status_code", [429, 500, 503])
def test_retryable_status_codes_are_retried(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    status_code: int,
) -> None:
    monkeypatch.setattr(
        "src.agents.gemini_multimodal_agent.time.sleep",
        lambda delay: None,
    )
    image_path = tmp_path / "page.png"
    write_png(image_path)
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(status_code, json={})
        return gemini_response(valid_payload())

    client = GeminiMultimodalClient(
        config=create_config(max_retries=1),
        http_client=httpx.Client(
            transport=httpx.MockTransport(handler),
            base_url="https://generativelanguage.googleapis.com/v1beta/",
        ),
    )

    result = client.chat_json(
        request=create_request(image_path),
        system_prompt="Return JSON.",
    )

    assert result["status"] == "success"
    assert calls == 2


def test_billing_credit_429_is_not_retried(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        "src.agents.gemini_multimodal_agent.time.sleep",
        lambda delay: None,
    )
    image_path = tmp_path / "page.png"
    write_png(image_path)
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

    client = GeminiMultimodalClient(
        config=create_config(max_retries=2),
        http_client=httpx.Client(
            transport=httpx.MockTransport(handler),
            base_url="https://generativelanguage.googleapis.com/v1beta/",
        ),
    )

    with pytest.raises(
        GeminiMultimodalProviderError,
        match="prepayment credits are depleted",
    ):
        client.chat_json(
            request=create_request(image_path),
            system_prompt="Return JSON.",
        )

    assert calls == 1


def test_400_is_not_retried(tmp_path: Path) -> None:
    image_path = tmp_path / "page.png"
    write_png(image_path)
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(400, json={"error": "bad request"})

    client = GeminiMultimodalClient(
        config=create_config(max_retries=2),
        http_client=httpx.Client(
            transport=httpx.MockTransport(handler),
            base_url="https://generativelanguage.googleapis.com/v1beta/",
        ),
    )

    with pytest.raises(
        GeminiMultimodalProviderError,
        match="HTTP status 400",
    ) as error:
        client.chat_json(
            request=create_request(image_path),
            system_prompt="Return JSON.",
        )

    assert "bad request" in str(error.value)
    assert calls == 1


@pytest.mark.parametrize("status_code", [401, 403])
def test_auth_errors_are_safe(
    tmp_path: Path,
    status_code: int,
) -> None:
    image_path = tmp_path / "page.png"
    write_png(image_path)

    client = GeminiMultimodalClient(
        config=create_config(),
        http_client=httpx.Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(status_code, json={})
            ),
            base_url="https://generativelanguage.googleapis.com/v1beta/",
        ),
    )

    with pytest.raises(GeminiMultimodalAuthenticationError) as error:
        client.chat_json(
            request=create_request(image_path),
            system_prompt="Return JSON.",
        )

    assert "secret-test-key" not in str(error.value)
    assert "Authorization" not in str(error.value)


def test_timeout_produces_safe_provider_error(
    tmp_path: Path,
) -> None:
    image_path = tmp_path / "page.png"
    write_png(image_path)

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("timeout")

    client = GeminiMultimodalClient(
        config=create_config(),
        http_client=httpx.Client(
            transport=httpx.MockTransport(handler),
            base_url="https://generativelanguage.googleapis.com/v1beta/",
        ),
    )

    with pytest.raises(GeminiMultimodalProviderError) as error:
        client.chat_json(
            request=create_request(image_path),
            system_prompt="Return JSON.",
        )

    assert "secret-test-key" not in str(error.value)
