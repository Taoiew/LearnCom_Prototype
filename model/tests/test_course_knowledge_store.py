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
from src.retrieval.course_knowledge_store import (
    CourseKnowledgeStore,
)


def _record(
    *,
    material_id: str,
    material_name: str,
    knowledge_id: str,
    content: str,
) -> FusedKnowledge:
    request_id = f"request-{knowledge_id}"
    now = datetime.now(timezone.utc)

    return FusedKnowledge(
        knowledge_id=knowledge_id,
        material_id=material_id,
        material_name=material_name,
        page_number=1,
        source_request_id=request_id,
        source_chunk_ids=[],
        asset_ids=[f"asset-{knowledge_id}"],
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


def _export_kb(
    *,
    root: Path,
    material_id: str,
    material_name: str,
    knowledge_id: str,
    content: str,
) -> Path:
    return VerifiedKBExporter().export(
        records=[
            _record(
                material_id=material_id,
                material_name=material_name,
                knowledge_id=knowledge_id,
                content=content,
            )
        ],
        material_id=material_id,
        material_name=material_name,
        kb_version="test-v1",
        output_dir=root / material_id,
    )


def test_activate_and_search_course_material(
    tmp_path: Path,
) -> None:
    kb_path = _export_kb(
        root=tmp_path,
        material_id="material-one",
        material_name="lesson.pdf",
        knowledge_id="knowledge-one",
        content="Uvicorn server and Visual Studio Code",
    )

    store = CourseKnowledgeStore()

    material_id = store.activate(
        course_id="CS242",
        class_session_id="week-07",
        verified_kb_path=kb_path,
    )

    assert material_id == "material-one"

    results = store.search(
        course_id="CS242",
        class_session_id="week-07",
        query="Uvicorn server",
        top_k=3,
    )

    assert results
    assert (
        results[0].chunk.material_id
        == "material-one"
    )


def test_course_sessions_are_isolated(
    tmp_path: Path,
) -> None:
    first_path = _export_kb(
        root=tmp_path / "first",
        material_id="material-one",
        material_name="week-07.pdf",
        knowledge_id="knowledge-one",
        content="Python custom exceptions",
    )

    second_path = _export_kb(
        root=tmp_path / "second",
        material_id="material-two",
        material_name="week-08.pdf",
        knowledge_id="knowledge-two",
        content="Operating system scheduling",
    )

    store = CourseKnowledgeStore()

    store.activate(
        course_id="CS242",
        class_session_id="week-07",
        verified_kb_path=first_path,
    )

    store.activate(
        course_id="CS242",
        class_session_id="week-08",
        verified_kb_path=second_path,
    )

    week_seven_results = store.search(
        course_id="CS242",
        class_session_id="week-07",
        query="scheduling",
        top_k=3,
    )

    week_eight_results = store.search(
        course_id="CS242",
        class_session_id="week-08",
        query="scheduling",
        top_k=3,
    )

    assert week_seven_results == []
    assert week_eight_results
    assert (
        week_eight_results[0].chunk.material_id
        == "material-two"
    )


def test_multiple_materials_in_same_session(
    tmp_path: Path,
) -> None:
    first_path = _export_kb(
        root=tmp_path / "first",
        material_id="material-one",
        material_name="lesson-one.pdf",
        knowledge_id="knowledge-one",
        content="Python inventory exceptions",
    )

    second_path = _export_kb(
        root=tmp_path / "second",
        material_id="material-two",
        material_name="lesson-two.png",
        knowledge_id="knowledge-two",
        content="Visual Studio Code Uvicorn server",
    )

    store = CourseKnowledgeStore()

    store.activate(
        course_id="CS242",
        class_session_id="week-07",
        verified_kb_path=first_path,
    )

    store.activate(
        course_id="CS242",
        class_session_id="week-07",
        verified_kb_path=second_path,
    )

    assert store.active_material_ids(
        course_id="CS242",
        class_session_id="week-07",
    ) == (
        "material-one",
        "material-two",
    )


def test_unknown_session_returns_empty_results() -> None:
    store = CourseKnowledgeStore()

    results = store.search(
        course_id="CS242",
        class_session_id="unknown",
        query="anything",
        top_k=3,
    )

    assert results == []