import pytest
from pydantic import ValidationError

from schemas.vision_contract import VisionRequest, VisionTask


def test_vision_request_defaults() -> None:
    request = VisionRequest(
        request_id="vision-request-001",
        material_id="material-001",
        material_name="lesson.pdf",
        page_number=2,
        asset_id="asset-18d318946af49d31",
        image_path=(
            "data/rendered_pages/"
            "material-001/page-0002.png"
        ),
    )

    assert request.request_id == "vision-request-001"
    assert request.material_id == "material-001"
    assert request.material_name == "lesson.pdf"
    assert request.page_number == 2
    assert request.asset_id == "asset-18d318946af49d31"
    assert request.mime_type == "image/png"
    assert request.extracted_text == ""
    assert request.prompt_version == "vision-v1"

    assert request.tasks == [
        VisionTask.DESCRIBE_VISUALS,
        VisionTask.EXTRACT_TEXT,
        VisionTask.EXTRACT_TABLES,
        VisionTask.EXPLAIN_RELATIONSHIPS,
    ]


def test_vision_request_rejects_invalid_page_number() -> None:
    with pytest.raises(ValidationError):
        VisionRequest(
            request_id="vision-request-invalid",
            material_id="material-001",
            material_name="lesson.pdf",
            page_number=0,
            asset_id="asset-invalid",
            image_path="page-0000.png",
        )