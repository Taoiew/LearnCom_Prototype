from datetime import datetime, timezone

import pytest

from schemas.fusion_contract import (
    ApprovalSource,
    SemanticApproval,
    SemanticDecision,
)
from schemas.kb_contract import ReviewStatus
from schemas.vision_contract import (
    VisualElement,
    VisualElementType,
    VisionResponse,
    VisionResponseStatus,
)
from src.evaluation.multimodal_verifier import (
    MultimodalVerificationResult,
)
from src.ingestion.pdf_ingestor import MaterialChunk
from src.service.text_vision_fusion import (
    TextVisionFusion,
)


def create_chunk(
    *,
    chunk_id: str = "chunk-001",
    material_id: str = "material-001",
    page_number: int = 2,
    chunk_index: int = 0,
    text: str = "Input flows into validation.",
) -> MaterialChunk:
    return MaterialChunk(
        chunk_id=chunk_id,
        material_id=material_id,
        material_name="lesson.pdf",
        page_number=page_number,
        chunk_index=chunk_index,
        text=text,
    )


def create_response(
    *,
    request_id: str = "vision-request-001",
    ocr_text: str = "",
    visual_elements: list[VisualElement] | None = None,
) -> VisionResponse:
    return VisionResponse(
        request_id=request_id,
        material_id="material-001",
        material_name="lesson.pdf",
        page_number=2,
        asset_id="asset-001",
        status=VisionResponseStatus.SUCCESS,
        page_summary="A learning pipeline diagram.",
        ocr_text=ocr_text,
        visual_elements=visual_elements or [
            VisualElement(
                element_id="element-001",
                element_type=VisualElementType.DIAGRAM,
                title="Validation",
                description=(
                    "The validation stage checks input."
                ),
                bounding_box=(
                    10.0,
                    20.0,
                    200.0,
                    300.0,
                ),
                confidence=0.92,
            )
        ],
        confidence=0.95,
        agent_model="external-vision-model",
        prompt_version="vision-v1",
    )


def create_verification(
    *,
    response: VisionResponse | None = None,
    review_status: ReviewStatus = (
        ReviewStatus.VERIFIED
    ),
    is_verified: bool = True,
) -> MultimodalVerificationResult:
    return MultimodalVerificationResult(
        response=response or create_response(),
        review_status=review_status,
        is_verified=is_verified,
        reasons=[],
    )


def create_approval(
    *,
    request_id: str = "vision-request-001",
    decision: SemanticDecision = (
        SemanticDecision.APPROVED
    ),
) -> SemanticApproval:
    return SemanticApproval(
        request_id=request_id,
        decision=decision,
        source=ApprovalSource.HUMAN,
        reviewer_id="reviewer-001",
        rationale="Visual evidence matches the page.",
        reviewed_at=datetime.now(timezone.utc),
    )


def test_fusion_preserves_provenance() -> None:
    fused = TextVisionFusion().fuse(
        source_chunks=[create_chunk()],
        verification=create_verification(),
        semantic_approval=create_approval(),
    )

    assert fused.material_id == "material-001"
    assert fused.page_number == 2
    assert fused.source_chunk_ids == ["chunk-001"]
    assert fused.asset_ids == ["asset-001"]
    assert fused.element_ids == ["element-001"]
    assert fused.review_status is ReviewStatus.VERIFIED


def test_fusion_requires_structural_verification() -> None:
    verification = create_verification(
        review_status=ReviewStatus.NEEDS_REVIEW,
        is_verified=False,
    )

    with pytest.raises(
        ValueError,
        match="structurally verified",
    ):
        TextVisionFusion().fuse(
            source_chunks=[create_chunk()],
            verification=verification,
            semantic_approval=create_approval(),
        )


def test_fusion_requires_semantic_approval() -> None:
    with pytest.raises(
        ValueError,
        match="explicit semantic approval",
    ):
        TextVisionFusion().fuse(
            source_chunks=[create_chunk()],
            verification=create_verification(),
            semantic_approval=create_approval(
                decision=SemanticDecision.REJECTED,
            ),
        )


def test_fusion_rejects_mismatched_approval() -> None:
    with pytest.raises(
        ValueError,
        match="does not match VisionResponse",
    ):
        TextVisionFusion().fuse(
            source_chunks=[create_chunk()],
            verification=create_verification(),
            semantic_approval=create_approval(
                request_id="different-request",
            ),
        )


def test_fusion_rejects_wrong_material_chunk() -> None:
    with pytest.raises(
        ValueError,
        match="material_id",
    ):
        TextVisionFusion().fuse(
            source_chunks=[
                create_chunk(
                    material_id="different-material",
                )
            ],
            verification=create_verification(),
            semantic_approval=create_approval(),
        )


def test_fusion_rejects_wrong_page_chunk() -> None:
    with pytest.raises(
        ValueError,
        match="page_number",
    ):
        TextVisionFusion().fuse(
            source_chunks=[
                create_chunk(page_number=3)
            ],
            verification=create_verification(),
            semantic_approval=create_approval(),
        )


def test_fusion_rejects_duplicate_chunk_ids() -> None:
    with pytest.raises(
        ValueError,
        match="duplicate chunk_id",
    ):
        TextVisionFusion().fuse(
            source_chunks=[
                create_chunk(),
                create_chunk(),
            ],
            verification=create_verification(),
            semantic_approval=create_approval(),
        )


def test_fusion_removes_duplicate_ocr_text() -> None:
    source_text = "Input flows into validation."

    response = create_response(
        ocr_text="  INPUT   FLOWS INTO VALIDATION. ",
    )

    fused = TextVisionFusion().fuse(
        source_chunks=[
            create_chunk(text=source_text)
        ],
        verification=create_verification(
            response=response
        ),
        semantic_approval=create_approval(),
    )

    assert fused.text_content == source_text
    assert (
        fused.visual_content.casefold().count(
            source_text.casefold()
        )
        == 0
    )


def test_fusion_keeps_distinct_ocr_text() -> None:
    response = create_response(
        ocr_text=(
            "Approved records are written "
            "to persistent storage."
        ),
    )

    fused = TextVisionFusion().fuse(
        source_chunks=[create_chunk()],
        verification=create_verification(
            response=response
        ),
        semantic_approval=create_approval(),
    )

    assert (
        "Approved records are written"
        in fused.visual_content
    )


def test_fusion_id_is_deterministic() -> None:
    fusion = TextVisionFusion()

    first = fusion.fuse(
        source_chunks=[create_chunk()],
        verification=create_verification(),
        semantic_approval=create_approval(),
    )
    second = fusion.fuse(
        source_chunks=[create_chunk()],
        verification=create_verification(),
        semantic_approval=create_approval(),
    )

    assert first.knowledge_id == second.knowledge_id
    assert first.knowledge_id.startswith("fused-")