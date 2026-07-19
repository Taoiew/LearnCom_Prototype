from pathlib import Path

import pytest

from schemas.vision_contract import (
    VisionRequest,
    VisionResponseStatus,
    VisualElementType,
)
from src.agents.multimodal_agent import (
    DemoMultimodalAgent,
    MultimodalAgent,
)


def create_vision_request(
    image_path: Path,
) -> VisionRequest:
    return VisionRequest(
        request_id="vision-request-001",
        material_id="material-001",
        material_name="lesson.pdf",
        page_number=2,
        asset_id="asset-18d318946af49d31",
        image_path=str(image_path),
        extracted_text="Custom Exceptions (Required)",
    )


def test_demo_multimodal_agent_returns_linked_response(
    tmp_path: Path,
) -> None:
    image_path = tmp_path / "page-0002.png"
    image_path.write_bytes(b"\x89PNG\r\n\x1a\n")

    request = create_vision_request(image_path)
    agent: MultimodalAgent = DemoMultimodalAgent()

    response = agent.analyze(request)

    assert response.request_id == request.request_id
    assert response.material_id == request.material_id
    assert response.material_name == request.material_name
    assert response.page_number == request.page_number
    assert response.asset_id == request.asset_id

    assert (
        response.status
        is VisionResponseStatus.NEEDS_REVIEW
    )
    assert response.confidence == 0.50
    assert response.agent_model == (
        "demo-multimodal-agent"
    )
    assert response.prompt_version == "vision-v1"

    assert response.ocr_text == request.extracted_text
    assert len(response.visual_elements) == 1
    assert len(response.warnings) == 1

    element = response.visual_elements[0]

    assert element.element_id.startswith("element-")
    assert (
        element.element_type
        is VisualElementType.IMAGE
    )
    assert (
        "No image-pixel inference was performed"
        in element.description
    )


def test_demo_element_id_is_deterministic(
    tmp_path: Path,
) -> None:
    image_path = tmp_path / "page-0002.png"
    image_path.write_bytes(b"\x89PNG\r\n\x1a\n")

    request = create_vision_request(image_path)
    agent = DemoMultimodalAgent()

    first_response = agent.analyze(request)
    second_response = agent.analyze(request)

    assert (
        first_response.visual_elements[0].element_id
        == second_response.visual_elements[0].element_id
    )


def test_demo_multimodal_agent_rejects_missing_image(
    tmp_path: Path,
) -> None:
    missing_path = tmp_path / "missing.png"
    request = create_vision_request(missing_path)

    agent = DemoMultimodalAgent()

    with pytest.raises(
        FileNotFoundError,
        match="Vision request image not found",
    ):
        agent.analyze(request)