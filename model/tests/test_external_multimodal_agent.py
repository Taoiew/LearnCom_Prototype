from pathlib import Path
from typing import Any

import pytest

from schemas.vision_contract import (
    VisionRequest,
    VisionResponseStatus,
    VisualElementType,
)
from src.agents.multimodal_agent import (
    ExternalMultimodalAgent,
)
from src.agents.multimodal_client import (
    MultimodalResponseError,
)


class FakeMultimodalClient:
    def __init__(
        self,
        result: dict[str, Any],
    ) -> None:
        self.result = result
        self.received_request: VisionRequest | None = None
        self.received_system_prompt = ""
        self.received_temperature: float | None = None

    def chat_json(
        self,
        request: VisionRequest,
        system_prompt: str,
        temperature: float = 0.0,
    ) -> dict[str, Any]:
        self.received_request = request
        self.received_system_prompt = system_prompt
        self.received_temperature = temperature
        return self.result


def create_request(
    image_path: Path,
) -> VisionRequest:
    return VisionRequest(
        request_id="vision-authoritative-001",
        material_id="material-001",
        material_name="lesson.pdf",
        page_number=2,
        asset_id="asset-page-002",
        image_path=str(image_path),
        mime_type="image/png",
        extracted_text="Custom Exceptions",
        prompt_version="vision-v1",
    )


def create_valid_payload() -> dict[str, Any]:
    return {
        "status": "success",
        "page_summary": (
            "A diagram maps inventory operations "
            "to custom exceptions."
        ),
        "ocr_text": "",
        "visual_elements": [
            {
                "element_id": "element-001",
                "element_type": "diagram",
                "title": "Exception flow",
                "description": (
                    "Arrows connect invalid operations "
                    "to exception classes."
                ),
                "extracted_text": (
                    "ProductExistsError"
                ),
                "bounding_box": [
                    50.0,
                    100.0,
                    600.0,
                    500.0,
                ],
                "confidence": 0.93,
            }
        ],
        "tables": [],
        "relationships": [],
        "warnings": [],
        "confidence": 0.93,
    }


def test_external_agent_returns_validated_response(
    tmp_path: Path,
) -> None:
    image_path = tmp_path / "page.png"
    image_path.write_bytes(b"\x89PNG\r\n\x1a\n")

    request = create_request(image_path)
    client = FakeMultimodalClient(
        create_valid_payload()
    )

    agent = ExternalMultimodalAgent(
        client=client,
        agent_model="external-vision-model",
    )

    response = agent.analyze(request)

    assert client.received_request is request
    assert client.received_temperature == 0.0
    assert "Do not add facts" in (
        client.received_system_prompt
    )

    assert response.request_id == request.request_id
    assert response.material_id == request.material_id
    assert response.material_name == request.material_name
    assert response.page_number == request.page_number
    assert response.asset_id == request.asset_id

    assert (
        response.status
        is VisionResponseStatus.SUCCESS
    )
    assert response.confidence == 0.93
    assert response.agent_model == (
        "external-vision-model"
    )
    assert response.prompt_version == "vision-v1"

    assert len(response.visual_elements) == 1
    assert (
        response.visual_elements[0].element_type
        is VisualElementType.DIAGRAM
    )


def test_external_agent_rejects_invalid_payload(
    tmp_path: Path,
) -> None:
    image_path = tmp_path / "page.png"
    image_path.write_bytes(b"\x89PNG\r\n\x1a\n")

    request = create_request(image_path)

    client = FakeMultimodalClient(
        {
            "status": "success",
            "page_summary": "",
            "confidence": 1.5,
        }
    )

    agent = ExternalMultimodalAgent(
        client=client,
        agent_model="external-vision-model",
    )

    with pytest.raises(
        MultimodalResponseError,
        match="does not match VisionResponse schema",
    ):
        agent.analyze(request)


def test_external_agent_rejects_empty_model_name() -> None:
    client = FakeMultimodalClient(
        create_valid_payload()
    )

    with pytest.raises(
        ValueError,
        match="agent_model must not be empty",
    ):
        ExternalMultimodalAgent(
            client=client,
            agent_model="",
        )