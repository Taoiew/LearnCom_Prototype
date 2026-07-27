import json
from pathlib import Path

from schemas.kb_contract import ReviewStatus
from schemas.vision_contract import (
    ExtractedTable,
    VisionRequest,
    VisionResponse,
    VisionResponseStatus,
    VisualRelationship,
    VisualElement,
    VisualElementType,
)
from src.agents.multimodal_agent import (
    DemoMultimodalAgent,
)
from src.evaluation.multimodal_verifier import (
    MultimodalVerifier,
)
from src.ingestion.vision_verification_exporter import (
    VisionVerificationExporter,
)


def create_request(
    image_path: Path,
) -> VisionRequest:
    return VisionRequest(
        request_id="vision-request-001",
        material_id="material-001",
        material_name="lesson.pdf",
        page_number=2,
        asset_id="asset-page-002",
        image_path=str(image_path),
        extracted_text="Exception flowchart",
        prompt_version="vision-v1",
    )


def create_verified_response(
    request: VisionRequest,
) -> VisionResponse:
    return VisionResponse(
        request_id=request.request_id,
        material_id=request.material_id,
        material_name=request.material_name,
        page_number=request.page_number,
        asset_id=request.asset_id,
        status=VisionResponseStatus.SUCCESS,
        page_summary=(
            "The flowchart maps invalid operations "
            "to custom exceptions."
        ),
        ocr_text="Exception flowchart",
        visual_elements=[
            VisualElement(
                element_id="element-001",
                element_type=VisualElementType.DIAGRAM,
                title="Exception flow",
                description=(
                    "Invalid operations point to the "
                    "corresponding exception classes."
                ),
                extracted_text="ProductExistsError",
                confidence=0.92,
            )
        ],
        confidence=0.92,
        agent_model="external-multimodal-model",
        prompt_version="vision-v1",
    )


def test_verifier_accepts_grounded_success_response(
    tmp_path: Path,
) -> None:
    image_path = tmp_path / "page.png"
    image_path.write_bytes(b"\x89PNG\r\n\x1a\n")

    request = create_request(image_path)
    response = create_verified_response(request)

    verifier = MultimodalVerifier(
        minimum_confidence=0.80
    )

    result = verifier.verify(
        request=request,
        response=response,
    )

    assert result.is_verified is True
    assert result.review_status is ReviewStatus.VERIFIED
    assert result.reasons == []
    assert result.response is response


def test_verifier_routes_demo_response_to_review(
    tmp_path: Path,
) -> None:
    image_path = tmp_path / "page.png"
    image_path.write_bytes(b"\x89PNG\r\n\x1a\n")

    request = create_request(image_path)
    response = DemoMultimodalAgent().analyze(request)

    verifier = MultimodalVerifier(
        minimum_confidence=0.80
    )

    result = verifier.verify(
        request=request,
        response=response,
    )

    assert result.is_verified is False
    assert (
        result.review_status
        is ReviewStatus.NEEDS_REVIEW
    )

    assert (
        "Demo multimodal output cannot be verified"
        in result.reasons
    )
    assert (
        "Response confidence is below 0.80"
        in result.reasons
    )


def test_verifier_rejects_mismatched_source_link(
    tmp_path: Path,
) -> None:
    image_path = tmp_path / "page.png"
    image_path.write_bytes(b"\x89PNG\r\n\x1a\n")

    request = create_request(image_path)
    valid_response = create_verified_response(request)

    invalid_response = valid_response.model_copy(
        update={
            "asset_id": "wrong-asset-id",
        }
    )

    verifier = MultimodalVerifier()

    result = verifier.verify(
        request=request,
        response=invalid_response,
    )

    assert result.is_verified is False
    assert result.review_status is ReviewStatus.REJECTED

    assert (
        "response asset_id does not match request"
        in result.reasons
    )


def test_verifier_rejects_failed_response(
    tmp_path: Path,
) -> None:
    image_path = tmp_path / "page.png"
    image_path.write_bytes(b"\x89PNG\r\n\x1a\n")

    request = create_request(image_path)
    valid_response = create_verified_response(request)

    failed_response = valid_response.model_copy(
        update={
            "status": VisionResponseStatus.FAILED,
        }
    )

    verifier = MultimodalVerifier()

    result = verifier.verify(
        request=request,
        response=failed_response,
    )

    assert result.is_verified is False
    assert result.review_status is ReviewStatus.REJECTED

    assert (
        "Multimodal agent returned failed status"
        in result.reasons
    )


def test_verifier_accepts_table_relationships_and_minor_box_overflow(
    tmp_path: Path,
) -> None:
    image_path = tmp_path / "page.png"
    image_path.write_bytes(b"\x89PNG\r\n\x1a\n")

    request = create_request(image_path).model_copy(
        update={
            "image_width_pixels": 960,
            "image_height_pixels": 840,
        }
    )
    response = create_verified_response(request).model_copy(
        update={
            "visual_elements": [],
            "tables": [
                ExtractedTable(
                    table_id="table_current",
                    headers=["Course", "Credit"],
                    rows=[["CS223", "3"]],
                    bounding_box=(24.0, 300.0, 976.0, 698.0),
                    confidence=0.95,
                ),
                ExtractedTable(
                    table_id="table_summary",
                    headers=["Category", "CR"],
                    rows=[["THIS SEMESTER", "21"]],
                    bounding_box=(24.0, 700.0, 976.0, 872.0),
                    confidence=0.95,
                ),
            ],
            "relationships": [
                VisualRelationship(
                    source_element_id="table_current",
                    target_element_id="table_summary",
                    relation="summarizes credits in",
                    confidence=0.9,
                )
            ],
            "warnings": [
                "Top row is partially cropped at the top edge."
            ],
        }
    )

    result = MultimodalVerifier().verify(
        request=request,
        response=response,
    )

    assert result.review_status is ReviewStatus.NEEDS_REVIEW
    assert result.is_verified is False
    assert result.reasons == [
        "Response contains multimodal warnings"
    ]


def test_batch_verifier_routes_demo_to_review_with_zero_verified(
    tmp_path: Path,
) -> None:
    image_path = tmp_path / "page.png"
    image_path.write_bytes(b"\x89PNG\r\n\x1a\n")

    request = create_request(image_path)
    response = DemoMultimodalAgent().analyze(request)

    batch = MultimodalVerifier(
        minimum_confidence=0.80
    ).verify_batch(
        requests=[request],
        responses=[response],
    )

    assert batch.verified_count == 0
    assert batch.needs_review_count == 1
    assert batch.rejected_count == 0
    assert batch.issues == []
    assert batch.results[0].review_status is (
        ReviewStatus.NEEDS_REVIEW
    )


def test_batch_verifier_reports_duplicate_and_missing_ids(
    tmp_path: Path,
) -> None:
    first_image = tmp_path / "first.png"
    second_image = tmp_path / "second.png"
    first_image.write_bytes(b"\x89PNG\r\n\x1a\n")
    second_image.write_bytes(b"\x89PNG\r\n\x1a\n")

    first_request = create_request(first_image)
    duplicate_request = create_request(first_image)
    missing_response_request = create_request(
        second_image
    ).model_copy(
        update={
            "request_id": "vision-request-002",
            "page_number": 3,
            "asset_id": "asset-page-003",
        }
    )

    orphan_response = create_verified_response(
        missing_response_request
    ).model_copy(
        update={
            "request_id": "orphan-response",
        }
    )

    batch = MultimodalVerifier().verify_batch(
        requests=[
            first_request,
            duplicate_request,
            missing_response_request,
        ],
        responses=[orphan_response],
    )

    assert batch.results == []
    assert batch.rejected_count == 3

    issue_reasons = {
        issue.request_id: issue.reasons
        for issue in batch.issues
    }

    assert issue_reasons["vision-request-001"] == [
        "Duplicate VisionRequest request_id"
    ]
    assert issue_reasons["vision-request-002"] == [
        "Missing VisionResponse for VisionRequest"
    ]
    assert issue_reasons["orphan-response"] == [
        "VisionResponse has no matching VisionRequest"
    ]


def test_verification_exporter_separates_review_buckets(
    tmp_path: Path,
) -> None:
    image_path = tmp_path / "page.png"
    image_path.write_bytes(b"\x89PNG\r\n\x1a\n")

    request = create_request(image_path)
    response = DemoMultimodalAgent().analyze(request)

    batch = MultimodalVerifier(
        minimum_confidence=0.80
    ).verify_batch(
        requests=[request],
        responses=[response],
    )

    output_path = VisionVerificationExporter().export(
        requests=[request],
        batch=batch,
        output_dir=tmp_path / "manifests",
    )

    payload = json.loads(
        output_path.read_text(encoding="utf-8")
    )

    assert output_path.name == "vision_verifications.json"
    assert payload["schema_version"] == "v1"
    assert payload["material_id"] == "material-001"
    assert payload["verified_count"] == 0
    assert payload["needs_review_count"] == 1
    assert payload["rejected_count"] == 0
    assert payload["verified"] == []
    assert payload["rejected"] == []
    assert payload["batch_issues"] == []

    review_record = payload["needs_review"][0]

    assert review_record["request_id"] == request.request_id
    assert review_record["review_status"] == "needs_review"
    assert review_record["is_verified"] is False
    assert review_record["response"]["agent_model"] == (
        "demo-multimodal-agent"
    )
