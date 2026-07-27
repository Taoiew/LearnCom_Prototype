import json
from pathlib import Path

import httpx
import pytest

from schemas.vision_contract import VisionRequest
from src.agents.multimodal_client import (
    MultimodalConfig,
    MultimodalImageError,
    MultimodalResponseError,
    OpenAICompatibleMultimodalClient,
)


def create_request(
    image_path: Path,
    mime_type: str = "image/png",
) -> VisionRequest:
    return VisionRequest(
        request_id="vision-request-001",
        material_id="material-001",
        material_name="lesson.pdf",
        page_number=2,
        asset_id="asset-page-002",
        image_path=str(image_path),
        mime_type=mime_type,
        extracted_text="Exception flowchart",
    )


def create_config(
    max_image_bytes: int = 1024,
) -> MultimodalConfig:
    return MultimodalConfig(
        base_url="https://provider.example/v1",
        model="vision-model",
        api_key="test-key",
        max_image_bytes=max_image_bytes,
    )


def test_multimodal_client_sends_image_and_parses_json(
    tmp_path: Path,
) -> None:
    image_path = tmp_path / "page.png"
    image_path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        b"test-image-content"
    )

    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        assert request.url.path == (
            "/v1/chat/completions"
        )
        assert request.headers["Authorization"] == (
            "Bearer test-key"
        )

        payload = json.loads(request.content)

        assert payload["model"] == "vision-model"
        assert payload["temperature"] == 0.0
        assert payload["response_format"] == {
            "type": "json_object"
        }

        user_content = payload[
            "messages"
        ][1]["content"]

        metadata = json.loads(
            user_content[0]["text"]
        )

        assert metadata["request_id"] == (
            "vision-request-001"
        )
        assert metadata["page_number"] == 2

        image_url = user_content[
            1
        ]["image_url"]["url"]

        assert image_url.startswith(
            "data:image/png;base64,"
        )

        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "status": "success",
                                    "confidence": 0.92,
                                }
                            )
                        }
                    }
                ]
            },
        )

    transport = httpx.MockTransport(handler)

    with httpx.Client(
        transport=transport,
        base_url="https://provider.example/v1/",
    ) as http_client:
        client = OpenAICompatibleMultimodalClient(
            config=create_config(),
            http_client=http_client,
        )

        result = client.chat_json(
            request=create_request(image_path),
            system_prompt="Return structured JSON.",
        )

    assert result["status"] == "success"
    assert result["confidence"] == 0.92


def test_multimodal_client_rejects_oversized_image(
    tmp_path: Path,
) -> None:
    image_path = tmp_path / "large.png"
    image_path.write_bytes(
        b"\x89PNG\r\n\x1a\n" + (b"x" * 100)
    )

    client = OpenAICompatibleMultimodalClient(
        config=create_config(
            max_image_bytes=16
        )
    )

    try:
        with pytest.raises(
            MultimodalImageError,
            match="exceeds configured size limit",
        ):
            client.chat_json(
                request=create_request(image_path),
                system_prompt="Return JSON.",
            )
    finally:
        client.close()


def test_multimodal_client_rejects_mime_mismatch(
    tmp_path: Path,
) -> None:
    image_path = tmp_path / "page.png"
    image_path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        b"test-image"
    )

    client = OpenAICompatibleMultimodalClient(
        config=create_config()
    )

    try:
        with pytest.raises(
            MultimodalImageError,
            match="does not match file content",
        ):
            client.chat_json(
                request=create_request(
                    image_path=image_path,
                    mime_type="image/jpeg",
                ),
                system_prompt="Return JSON.",
            )
    finally:
        client.close()


def test_multimodal_client_rejects_invalid_response(
    tmp_path: Path,
) -> None:
    image_path = tmp_path / "page.png"
    image_path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        b"test-image"
    )

    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": "not-json"
                        }
                    }
                ]
            },
        )

    transport = httpx.MockTransport(handler)

    with httpx.Client(
        transport=transport,
        base_url="https://provider.example/v1/",
    ) as http_client:
        client = OpenAICompatibleMultimodalClient(
            config=create_config(),
            http_client=http_client,
        )

        with pytest.raises(
            MultimodalResponseError,
            match="not valid structured JSON",
        ):
            client.chat_json(
                request=create_request(image_path),
                system_prompt="Return JSON.",
            )