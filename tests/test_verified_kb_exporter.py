import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from schemas.fusion_contract import (
    ApprovalSource,
    FusedKnowledge,
    SemanticApproval,
    SemanticDecision,
)
from schemas.kb_contract import ReviewStatus
from src.ingestion.verified_kb_exporter import (
    VerifiedKBExporter,
)


def create_approval(
    request_id: str,
) -> SemanticApproval:
    return SemanticApproval(
        request_id=request_id,
        decision=SemanticDecision.APPROVED,
        source=ApprovalSource.HUMAN,
        reviewer_id="reviewer-001",
        rationale="Evidence matches the source page.",
        reviewed_at=datetime(
            2026,
            7,
            20,
            3,
            0,
            tzinfo=timezone.utc,
        ),
    )


def create_record(
    *,
    knowledge_id: str = "fused-001",
    material_id: str = "material-001",
    material_name: str = "lesson.pdf",
    page_number: int = 2,
) -> FusedKnowledge:
    request_id = f"vision-{knowledge_id}"

    return FusedKnowledge(
        knowledge_id=knowledge_id,
        material_id=material_id,
        material_name=material_name,
        page_number=page_number,
        source_request_id=request_id,
        source_chunk_ids=[
            f"chunk-{page_number:04d}",
        ],
        asset_ids=[
            f"asset-{page_number:04d}",
        ],
        element_ids=[
            f"element-{page_number:04d}",
        ],
        table_ids=[],
        text_content="Source text.",
        visual_content="Verified visual description.",
        content=(
            "Source text.\n\n"
            "Verified visual description."
        ),
        confidence=0.92,
        review_status=ReviewStatus.VERIFIED,
        agent_model="external-vision-model",
        prompt_version="vision-v1",
        fusion_version="fusion-v1",
        semantic_approval=create_approval(
            request_id=request_id,
        ),
        created_at=datetime(
            2026,
            7,
            20,
            3,
            5,
            tzinfo=timezone.utc,
        ),
    )


def read_payload(path: Path) -> dict:
    return json.loads(
        path.read_text(encoding="utf-8")
    )


def test_export_verified_kb(
    tmp_path: Path,
) -> None:
    output_path = VerifiedKBExporter().export(
        records=[create_record()],
        material_id="material-001",
        material_name="lesson.pdf",
        kb_version="kb-2026-07-20-001",
        output_dir=tmp_path,
    )

    assert output_path.exists()
    assert output_path.name == "verified_kb.json"

    payload = read_payload(output_path)

    assert payload["schema_version"] == "v1"
    assert payload["kb_version"] == (
        "kb-2026-07-20-001"
    )
    assert payload["material_id"] == "material-001"
    assert payload["material_name"] == "lesson.pdf"
    assert payload["total_records"] == 1
    assert len(payload["content_sha256"]) == 64
    assert payload["records"][0]["knowledge_id"] == (
        "fused-001"
    )
    assert (
        payload["records"][0]["review_status"]
        == "verified"
    )


def test_export_orders_records_deterministically(
    tmp_path: Path,
) -> None:
    records = [
        create_record(
            knowledge_id="fused-page-3",
            page_number=3,
        ),
        create_record(
            knowledge_id="fused-page-1",
            page_number=1,
        ),
        create_record(
            knowledge_id="fused-page-2",
            page_number=2,
        ),
    ]

    output_path = VerifiedKBExporter().export(
        records=records,
        material_id="material-001",
        material_name="lesson.pdf",
        kb_version="kb-v1",
        output_dir=tmp_path,
    )

    payload = read_payload(output_path)

    assert [
        record["page_number"]
        for record in payload["records"]
    ] == [1, 2, 3]


def test_content_hash_is_deterministic(
    tmp_path: Path,
) -> None:
    records = [
        create_record(
            knowledge_id="fused-002",
            page_number=2,
        ),
        create_record(
            knowledge_id="fused-001",
            page_number=1,
        ),
    ]

    first_path = VerifiedKBExporter().export(
        records=records,
        material_id="material-001",
        material_name="lesson.pdf",
        kb_version="kb-v1",
        output_dir=tmp_path / "first",
    )
    second_path = VerifiedKBExporter().export(
        records=list(reversed(records)),
        material_id="material-001",
        material_name="lesson.pdf",
        kb_version="kb-v1",
        output_dir=tmp_path / "second",
    )

    first = read_payload(first_path)
    second = read_payload(second_path)

    assert (
        first["content_sha256"]
        == second["content_sha256"]
    )


def test_export_rejects_wrong_material(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        ValueError,
        match="material_id",
    ):
        VerifiedKBExporter().export(
            records=[
                create_record(
                    material_id="different-material",
                )
            ],
            material_id="material-001",
            material_name="lesson.pdf",
            kb_version="kb-v1",
            output_dir=tmp_path,
        )


def test_export_rejects_duplicate_knowledge_id(
    tmp_path: Path,
) -> None:
    record = create_record()

    with pytest.raises(
        ValueError,
        match="duplicate knowledge_id",
    ):
        VerifiedKBExporter().export(
            records=[record, record],
            material_id="material-001",
            material_name="lesson.pdf",
            kb_version="kb-v1",
            output_dir=tmp_path,
        )


def test_export_allows_empty_verified_kb(
    tmp_path: Path,
) -> None:
    output_path = VerifiedKBExporter().export(
        records=[],
        material_id="material-001",
        material_name="lesson.pdf",
        kb_version="kb-empty",
        output_dir=tmp_path,
    )

    payload = read_payload(output_path)

    assert payload["total_records"] == 0
    assert payload["records"] == []
    assert len(payload["content_sha256"]) == 64


def test_export_replaces_existing_file_atomically(
    tmp_path: Path,
) -> None:
    exporter = VerifiedKBExporter()

    output_path = exporter.export(
        records=[
            create_record(
                knowledge_id="fused-old",
            )
        ],
        material_id="material-001",
        material_name="lesson.pdf",
        kb_version="kb-old",
        output_dir=tmp_path,
    )

    exporter.export(
        records=[
            create_record(
                knowledge_id="fused-new",
            )
        ],
        material_id="material-001",
        material_name="lesson.pdf",
        kb_version="kb-new",
        output_dir=tmp_path,
    )

    payload = read_payload(output_path)

    assert payload["kb_version"] == "kb-new"
    assert payload["records"][0]["knowledge_id"] == (
        "fused-new"
    )

    temporary_files = list(
        tmp_path.glob(".verified-kb-*.tmp")
    )

    assert temporary_files == []