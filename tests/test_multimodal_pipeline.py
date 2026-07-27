from pathlib import Path

import pytest

from schemas.vision_contract import (
    VisionRequest,
    VisionResponse,
    VisionResponseStatus,
)
from src.agents.multimodal_agent import (
    DemoMultimodalAgent,
    MultimodalAgent,
)
from src.service.multimodal_pipeline import (
    MultimodalPipeline,
)


def create_request(
    image_path: Path,
    request_id: str = "vision-request-001",
    page_number: int = 2,
) -> VisionRequest:
    return VisionRequest(
        request_id=request_id,
        material_id="material-001",
        material_name="lesson.pdf",
        page_number=page_number,
        asset_id=f"asset-page-{page_number}",
        image_path=str(image_path),
        extracted_text=f"Page {page_number} text",
    )


def test_pipeline_processes_requests_in_order(
    tmp_path: Path,
) -> None:
    first_image = tmp_path / "page-0002.png"
    second_image = tmp_path / "page-0003.png"

    first_image.write_bytes(b"\x89PNG\r\n\x1a\n")
    second_image.write_bytes(b"\x89PNG\r\n\x1a\n")

    requests = [
        create_request(
            image_path=first_image,
            request_id="vision-request-001",
            page_number=2,
        ),
        create_request(
            image_path=second_image,
            request_id="vision-request-002",
            page_number=3,
        ),
    ]

    pipeline = MultimodalPipeline(
        agent=DemoMultimodalAgent()
    )

    responses = pipeline.process(requests)

    assert len(responses) == 2

    assert responses[0].request_id == (
        "vision-request-001"
    )
    assert responses[0].page_number == 2

    assert responses[1].request_id == (
        "vision-request-002"
    )
    assert responses[1].page_number == 3


def test_pipeline_accepts_empty_request_list() -> None:
    pipeline = MultimodalPipeline(
        agent=DemoMultimodalAgent()
    )

    responses = pipeline.process([])

    assert responses == []


def test_pipeline_rejects_duplicate_request_ids(
    tmp_path: Path,
) -> None:
    image_path = tmp_path / "page.png"
    image_path.write_bytes(b"\x89PNG\r\n\x1a\n")

    requests = [
        create_request(
            image_path=image_path,
            request_id="duplicate-request",
            page_number=2,
        ),
        create_request(
            image_path=image_path,
            request_id="duplicate-request",
            page_number=3,
        ),
    ]

    pipeline = MultimodalPipeline(
        agent=DemoMultimodalAgent()
    )

    with pytest.raises(
        ValueError,
        match="Duplicate VisionRequest request_id",
    ):
        pipeline.process(requests)


class IncorrectResponseAgent(MultimodalAgent):
    def analyze(
        self,
        request: VisionRequest,
    ) -> VisionResponse:
        return VisionResponse(
            request_id="wrong-request-id",
            material_id=request.material_id,
            material_name=request.material_name,
            page_number=request.page_number,
            asset_id=request.asset_id,
            status=VisionResponseStatus.SUCCESS,
            page_summary="Incorrect linked response",
            confidence=0.9,
            agent_model="incorrect-test-agent",
        )


def test_pipeline_rejects_mismatched_response(
    tmp_path: Path,
) -> None:
    image_path = tmp_path / "page.png"
    image_path.write_bytes(b"\x89PNG\r\n\x1a\n")

    request = create_request(
        image_path=image_path,
    )

    pipeline = MultimodalPipeline(
        agent=IncorrectResponseAgent()
    )

    with pytest.raises(
        ValueError,
        match=(
            "VisionResponse request_id does not "
            "match VisionRequest"
        ),
    ):
        pipeline.process([request])