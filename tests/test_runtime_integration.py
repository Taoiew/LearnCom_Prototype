from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from schemas.fusion_contract import (
    ApprovalSource,
    FusedKnowledge,
    SemanticApproval,
    SemanticDecision,
)
from schemas.kb_contract import ReviewStatus
from schemas.model_contract import (
    ChatRequest,
    LearningPhase,
    ScopeDecision,
)
from src.ingestion.verified_kb_exporter import (
    VerifiedKBExporter,
)
from src.service.api import create_app
from src.service.runtime import (
    ModelRuntimeConfig,
    RuntimeConfigurationError,
    build_pipeline,
    build_pipeline_from_environment,
)


class FakeLocalLLMClient:
    def __init__(self) -> None:
        self.call_count = 0
        self.user_prompt = ""

    def chat_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
    ) -> dict[str, Any]:
        self.call_count += 1
        self.user_prompt = user_prompt

        return {
            "answer": (
                "Gradient descent ปรับพารามิเตอร์"
                "เพื่อลดค่า loss"
            ),
            "confidence": 0.91,
            "learning_signals": [],
        }


def create_verified_kb(
    tmp_path: Path,
) -> Path:
    request_id = "vision-gradient-001"

    approval = SemanticApproval(
        request_id=request_id,
        decision=SemanticDecision.APPROVED,
        source=ApprovalSource.HUMAN,
        reviewer_id="reviewer-001",
        rationale="Verified against source material.",
        reviewed_at=datetime(
            2026,
            7,
            20,
            3,
            0,
            tzinfo=timezone.utc,
        ),
    )

    record = FusedKnowledge(
        knowledge_id="fused-gradient-001",
        material_id="material-001",
        material_name="lesson.pdf",
        page_number=2,
        source_request_id=request_id,
        source_chunk_ids=[
            "chunk-source-001",
        ],
        asset_ids=[
            "asset-page-0002",
        ],
        element_ids=[
            "element-gradient-001",
        ],
        table_ids=[],
        text_content=(
            "Gradient descent updates parameters."
        ),
        visual_content=(
            "The diagram shows loss decreasing "
            "after repeated parameter updates."
        ),
        content=(
            "Gradient descent updates model parameters "
            "in the opposite direction of the gradient "
            "to reduce the loss function."
        ),
        confidence=0.94,
        review_status=ReviewStatus.VERIFIED,
        agent_model="external-vision-model",
        prompt_version="vision-v1",
        fusion_version="fusion-v1",
        semantic_approval=approval,
        created_at=datetime(
            2026,
            7,
            20,
            3,
            5,
            tzinfo=timezone.utc,
        ),
    )

    return VerifiedKBExporter().export(
        records=[record],
        material_id="material-001",
        material_name="lesson.pdf",
        kb_version="kb-runtime-test",
        output_dir=tmp_path,
    )


def verified_environment(
    kb_path: Path,
) -> dict[str, str]:
    return {
        "MODEL_RUNTIME_MODE": "verified_kb",
        "VERIFIED_KB_PATH": str(kb_path),
        "LOCAL_LLM_BASE_URL": (
            "http://127.0.0.1:8000/v1"
        ),
        "LOCAL_LLM_API_KEY": "local",
        "LOCAL_LLM_MODEL": "test-local-model",
        "LLM_TIMEOUT_SECONDS": "30",
        "RAG_TOP_K": "2",
        "RAG_MAX_CONTEXT_CHARS": "4000",
        "MATERIAL_SCOPE_THRESHOLD": "0.10",
        "COURSE_SCOPE_THRESHOLD": "0.60",
    }


def create_chat_request() -> ChatRequest:
    return ChatRequest(
        student_id="student-001",
        course_id="course-001",
        class_session_id="session-001",
        phase=LearningPhase.DURING_CLASS,
        question=(
            "How does gradient descent reduce loss?"
        ),
    )


def test_runtime_defaults_to_demo_mode():
    config = ModelRuntimeConfig.from_environment({})

    assert config.mode == "demo"
    assert config.verified_kb_path is None
    assert config.top_k == 3
    assert config.max_context_chars == 12000


def test_runtime_rejects_unknown_mode():
    with pytest.raises(
        RuntimeConfigurationError,
        match="MODEL_RUNTIME_MODE",
    ):
        ModelRuntimeConfig.from_environment(
            {
                "MODEL_RUNTIME_MODE": "unknown",
            }
        )


def test_verified_mode_requires_kb_path():
    with pytest.raises(
        RuntimeConfigurationError,
        match="VERIFIED_KB_PATH",
    ):
        ModelRuntimeConfig.from_environment(
            {
                "MODEL_RUNTIME_MODE": "verified_kb",
                "LOCAL_LLM_MODEL": "local-model",
            }
        )


def test_verified_mode_requires_local_model(
    tmp_path: Path,
):
    kb_path = create_verified_kb(tmp_path)
    environment = verified_environment(kb_path)
    environment["LOCAL_LLM_MODEL"] = ""

    with pytest.raises(
        RuntimeConfigurationError,
        match="LOCAL_LLM_MODEL",
    ):
        ModelRuntimeConfig.from_environment(
            environment
        )


def test_runtime_rejects_invalid_top_k():
    with pytest.raises(
        RuntimeConfigurationError,
        match="RAG_TOP_K",
    ):
        ModelRuntimeConfig.from_environment(
            {
                "RAG_TOP_K": "0",
            }
        )


def test_demo_pipeline_still_answers():
    config = ModelRuntimeConfig.from_environment(
        {
            "MODEL_RUNTIME_MODE": "demo",
        }
    )

    pipeline = build_pipeline(config)

    response = pipeline.run(
        request=create_chat_request(),
        course_relevance_score=0.90,
    )

    assert response.scope is ScopeDecision.IN_MATERIAL
    assert response.confidence == 0.90
    assert len(response.citations) == 1


def test_verified_pipeline_uses_local_llm(
    tmp_path: Path,
):
    kb_path = create_verified_kb(tmp_path)
    fake_llm = FakeLocalLLMClient()

    pipeline = build_pipeline_from_environment(
        environment=verified_environment(kb_path),
        llm_client=fake_llm,
    )

    response = pipeline.run(
        request=create_chat_request(),
        course_relevance_score=0.90,
    )

    assert fake_llm.call_count == 1
    assert response.scope is ScopeDecision.IN_MATERIAL
    assert response.confidence == 0.91
    assert (
        response.answer
        == "Gradient descent ปรับพารามิเตอร์"
        "เพื่อลดค่า loss"
    )


def test_verified_pipeline_returns_full_provenance(
    tmp_path: Path,
):
    kb_path = create_verified_kb(tmp_path)

    pipeline = build_pipeline_from_environment(
        environment=verified_environment(kb_path),
        llm_client=FakeLocalLLMClient(),
    )

    response = pipeline.run(
        request=create_chat_request(),
        course_relevance_score=0.90,
    )

    assert len(response.citations) == 1

    citation = response.citations[0]

    assert citation.material_id == "material-001"
    assert citation.material_name == "lesson.pdf"
    assert (
        citation.knowledge_id
        == "fused-gradient-001"
    )
    assert citation.chunk_id == "fused-gradient-001"
    assert citation.source_chunk_ids == [
        "chunk-source-001"
    ]
    assert citation.asset_ids == [
        "asset-page-0002"
    ]
    assert citation.page_number == 2
    assert citation.relevance_score > 0


def test_verified_kb_to_chat_api_end_to_end(
    tmp_path: Path,
):
    kb_path = create_verified_kb(tmp_path)
    fake_llm = FakeLocalLLMClient()

    pipeline = build_pipeline_from_environment(
        environment=verified_environment(kb_path),
        llm_client=fake_llm,
    )

    client = TestClient(create_app(pipeline))

    response = client.post(
        "/v1/chat",
        json={
            "request": {
                "student_id": "student-001",
                "course_id": "course-001",
                "class_session_id": "session-001",
                "phase": "during_class",
                "question": (
                    "How does gradient descent reduce loss?"
                ),
            },
            "course_relevance_score": 0.90,
            "unsafe": False,
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["scope"] == "in_material"
    assert body["used_external_agent"] is False
    assert body["confidence"] == 0.91

    citation = body["citations"][0]

    assert (
        citation["knowledge_id"]
        == "fused-gradient-001"
    )
    assert citation["source_chunk_ids"] == [
        "chunk-source-001"
    ]
    assert citation["asset_ids"] == [
        "asset-page-0002"
    ]


def test_runtime_rejects_tampered_verified_kb(
    tmp_path: Path,
):
    kb_path = create_verified_kb(tmp_path)

    content = kb_path.read_text(
        encoding="utf-8"
    )

    kb_path.write_text(
        content.replace(
            "reduce the loss function",
            "fabricated unsupported content",
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="content_sha256 mismatch",
    ):
        build_pipeline_from_environment(
            environment=verified_environment(
                kb_path
            ),
            llm_client=FakeLocalLLMClient(),
        )