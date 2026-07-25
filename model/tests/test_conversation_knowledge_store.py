from datetime import datetime, timezone
from pathlib import Path

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
from src.retrieval.conversation_knowledge_store import (
    ConversationKnowledgeStore,
)


def _export_kb(
    *,
    root: Path,
    material_id: str,
    content: str,
) -> Path:
    request_id = f"request-{material_id}"
    now = datetime.now(timezone.utc)

    record = FusedKnowledge(
        knowledge_id=f"knowledge-{material_id}",
        material_id=material_id,
        material_name=f"{material_id}.png",
        page_number=1,
        source_request_id=request_id,
        source_chunk_ids=[],
        asset_ids=[f"asset-{material_id}"],
        element_ids=[],
        table_ids=[],
        text_content="",
        visual_content=content,
        content=content,
        confidence=0.9,
        review_status=ReviewStatus.VERIFIED,
        agent_model="test-model",
        prompt_version="test-v1",
        fusion_version="fusion-v1",
        semantic_approval=SemanticApproval(
            request_id=request_id,
            decision=SemanticDecision.APPROVED,
            source=ApprovalSource.HUMAN,
            reviewer_id="tester",
            rationale="Approved for test",
            reviewed_at=now,
        ),
        created_at=now,
    )

    return VerifiedKBExporter().export(
        records=[record],
        material_id=material_id,
        material_name=f"{material_id}.png",
        kb_version="test-v1",
        output_dir=root / material_id,
    )


def test_conversations_are_isolated(
    tmp_path: Path,
) -> None:
    first_kb = _export_kb(
        root=tmp_path / "first",
        material_id="attachment-one",
        content="Uvicorn terminal screenshot",
    )

    second_kb = _export_kb(
        root=tmp_path / "second",
        material_id="attachment-two",
        content="Python inventory exceptions",
    )

    store = ConversationKnowledgeStore()

    store.activate_attachment(
        student_id="student-one",
        conversation_id="conversation-one",
        verified_kb_path=first_kb,
    )

    store.activate_attachment(
        student_id="student-two",
        conversation_id="conversation-two",
        verified_kb_path=second_kb,
    )

    first_results = store.search(
        student_id="student-one",
        conversation_id="conversation-one",
        query="Uvicorn",
        top_k=3,
    )

    leaked_results = store.search(
        student_id="student-two",
        conversation_id="conversation-two",
        query="Uvicorn",
        top_k=3,
    )

    assert first_results
    assert leaked_results == []


def test_clear_conversation_removes_attachments(
    tmp_path: Path,
) -> None:
    kb_path = _export_kb(
        root=tmp_path,
        material_id="attachment-one",
        content="Visual Studio Code screenshot",
    )

    store = ConversationKnowledgeStore()

    store.activate_attachment(
        student_id="student-one",
        conversation_id="conversation-one",
        verified_kb_path=kb_path,
    )

    removed = store.clear_conversation(
        student_id="student-one",
        conversation_id="conversation-one",
    )

    assert removed is True

    assert store.active_attachment_ids(
        student_id="student-one",
        conversation_id="conversation-one",
    ) == ()