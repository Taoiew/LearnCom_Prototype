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
from src.ingestion.pdf_ingestor import (
    ChunkType,
    SourceType,
)
from src.ingestion.verified_kb_exporter import (
    VerifiedKBExporter,
)
from src.retrieval.verified_kb_loader import (
    VerifiedKBLoadError,
    VerifiedKBLoader,
)
from src.retrieval.verified_kb_retriever import (
    VerifiedKBRetriever,
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
    page_number: int = 2,
    content: str = (
        "Gradient descent updates model parameters "
        "to reduce the loss function."
    ),
    text_content: str = (
        "Gradient descent updates parameters."
    ),
    visual_content: str = (
        "The diagram shows repeated parameter updates."
    ),
) -> FusedKnowledge:
    request_id = f"vision-{knowledge_id}"

    return FusedKnowledge(
        knowledge_id=knowledge_id,
        material_id="material-001",
        material_name="lesson.pdf",
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
        text_content=text_content,
        visual_content=visual_content,
        content=content,
        confidence=0.92,
        review_status=ReviewStatus.VERIFIED,
        agent_model="external-vision-model",
        prompt_version="vision-v1",
        fusion_version="fusion-v1",
        semantic_approval=create_approval(
            request_id
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


def export_kb(
    tmp_path: Path,
    records: list[FusedKnowledge] | None = None,
) -> Path:
    return VerifiedKBExporter().export(
        records=(
            [create_record()]
            if records is None
            else records
        ),
        material_id="material-001",
        material_name="lesson.pdf",
        kb_version="kb-test-v1",
        output_dir=tmp_path,
    )


def read_payload(path: Path) -> dict:
    return json.loads(
        path.read_text(encoding="utf-8")
    )


def write_payload(
    path: Path,
    payload: dict,
) -> None:
    path.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def test_loader_reads_verified_kb_metadata(
    tmp_path: Path,
) -> None:
    kb_path = export_kb(tmp_path)

    loaded = VerifiedKBLoader().load(kb_path)

    assert loaded.schema_version == "v1"
    assert loaded.kb_version == "kb-test-v1"
    assert loaded.material_id == "material-001"
    assert loaded.material_name == "lesson.pdf"
    assert loaded.generated_at.tzinfo is not None
    assert len(loaded.content_sha256) == 64
    assert len(loaded.records) == 1


def test_loader_converts_records_to_chunks_with_provenance(
    tmp_path: Path,
) -> None:
    kb_path = export_kb(tmp_path)

    loaded = VerifiedKBLoader().load(kb_path)
    chunks = loaded.to_material_chunks()

    assert len(chunks) == 1

    chunk = chunks[0]

    assert chunk.chunk_id == "fused-001"
    assert chunk.page_number == 2
    assert chunk.chunk_type is ChunkType.MIXED
    assert chunk.source_type is SourceType.MIXED
    assert chunk.image_ids == ("asset-0002",)
    assert chunk.source_chunk_ids == (
        "chunk-0002",
    )


def test_retriever_returns_relevant_verified_record(
    tmp_path: Path,
) -> None:
    kb_path = export_kb(
        tmp_path,
        records=[
            create_record(
                knowledge_id="fused-gradient",
                page_number=2,
                content=(
                    "Gradient descent reduces loss by "
                    "updating model parameters."
                ),
            ),
            create_record(
                knowledge_id="fused-database",
                page_number=3,
                content=(
                    "A relational database stores rows "
                    "inside tables."
                ),
                text_content=(
                    "A relational database stores rows."
                ),
                visual_content="",
            ),
        ],
    )

    retriever = VerifiedKBRetriever.from_file(
        kb_path
    )

    results = retriever.search(
        query="How does gradient descent reduce loss?",
        top_k=1,
    )

    assert len(results) == 1
    assert (
        results[0].chunk.chunk_id
        == "fused-gradient"
    )
    assert results[0].score > 0


def test_retriever_preserves_kb_metadata(
    tmp_path: Path,
) -> None:
    kb_path = export_kb(tmp_path)

    retriever = VerifiedKBRetriever.from_file(
        kb_path
    )

    assert (
        retriever.verified_kb.kb_version
        == "kb-test-v1"
    )
    assert (
        retriever.verified_kb.material_id
        == "material-001"
    )


def test_loader_allows_empty_verified_kb(
    tmp_path: Path,
) -> None:
    kb_path = export_kb(
        tmp_path,
        records=[],
    )

    loaded = VerifiedKBLoader().load(kb_path)
    retriever = VerifiedKBRetriever(loaded)

    assert loaded.records == ()
    assert loaded.to_material_chunks() == []
    assert retriever.search("anything") == []


def test_loader_rejects_missing_file(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        FileNotFoundError,
        match="Verified KB not found",
    ):
        VerifiedKBLoader().load(
            tmp_path / "missing.json"
        )


def test_loader_rejects_invalid_json(
    tmp_path: Path,
) -> None:
    kb_path = tmp_path / "verified_kb.json"

    kb_path.write_text(
        "{invalid-json",
        encoding="utf-8",
    )

    with pytest.raises(
        VerifiedKBLoadError,
        match="invalid JSON",
    ):
        VerifiedKBLoader().load(kb_path)


def test_loader_rejects_unsupported_schema(
    tmp_path: Path,
) -> None:
    kb_path = export_kb(tmp_path)
    payload = read_payload(kb_path)

    payload["schema_version"] = "v999"

    write_payload(kb_path, payload)

    with pytest.raises(
        VerifiedKBLoadError,
        match="Unsupported.*schema_version",
    ):
        VerifiedKBLoader().load(kb_path)


def test_loader_rejects_total_record_mismatch(
    tmp_path: Path,
) -> None:
    kb_path = export_kb(tmp_path)
    payload = read_payload(kb_path)

    payload["total_records"] = 99

    write_payload(kb_path, payload)

    with pytest.raises(
        VerifiedKBLoadError,
        match="total_records does not match",
    ):
        VerifiedKBLoader().load(kb_path)


def test_loader_rejects_tampered_content(
    tmp_path: Path,
) -> None:
    kb_path = export_kb(tmp_path)
    payload = read_payload(kb_path)

    payload["records"][0]["content"] = (
        "Tampered unverified content."
    )

    write_payload(kb_path, payload)

    with pytest.raises(
        VerifiedKBLoadError,
        match="content_sha256 mismatch",
    ):
        VerifiedKBLoader().load(kb_path)