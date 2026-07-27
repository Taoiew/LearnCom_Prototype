import json
from typing import Any

import pytest

from schemas.model_contract import LearningPhase
from src.agents.answer_agent import (
    RAGAnswerAgent,
    RAGAnswerAgentError,
)
from src.ingestion.pdf_ingestor import (
    ChunkType,
    MaterialChunk,
    SourceType,
)
from src.retrieval.in_memory_retriever import (
    RetrievedChunk,
)


class FakeLLMClient:
    def __init__(
        self,
        result: Any | None = None,
    ) -> None:
        self.result = (
            {
                "answer": (
                    "ลองอธิบายความหมายของ gradient ก่อน"
                ),
                "confidence": 0.85,
                "learning_signals": [
                    {
                        "topic": "Gradient Descent",
                        "signal_type": "readiness_gap",
                        "severity": 0.40,
                        "explanation": (
                            "ยังไม่แน่ใจเรื่อง gradient"
                        ),
                    }
                ],
            }
            if result is None
            else result
        )

        self.system_prompt = ""
        self.user_prompt = ""
        self.temperature: float | None = None

    def chat_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
    ) -> Any:
        self.system_prompt = system_prompt
        self.user_prompt = user_prompt
        self.temperature = temperature

        return self.result


def create_retrieved_chunk(
    *,
    chunk_id: str = "fused-gradient",
    text: str = (
        "Gradient descent updates model parameters "
        "to reduce loss."
    ),
    score: float = 0.90,
) -> RetrievedChunk:
    chunk = MaterialChunk(
        chunk_id=chunk_id,
        material_id="material-001",
        material_name="lesson.pdf",
        page_number=2,
        chunk_index=0,
        text=text,
        chunk_type=ChunkType.MIXED,
        source_type=SourceType.MIXED,
        image_ids=(
            "asset-0002",
        ),
        source_chunk_ids=(
            "chunk-0002",
        ),
    )

    return RetrievedChunk(
        chunk=chunk,
        score=score,
    )


def test_pre_class_answer_uses_readiness_instruction():
    fake_client = FakeLLMClient()
    agent = RAGAnswerAgent(fake_client)

    draft = agent.answer(
        question="Gradient descent คืออะไร",
        phase=LearningPhase.PRE_CLASS,
        retrieved_chunks=[
            create_retrieved_chunk()
        ],
    )

    assert "PRE-CLASS" in fake_client.system_prompt
    assert (
        "Do not reveal the complete answer"
        in fake_client.system_prompt
    )
    assert draft.confidence == 0.85
    assert len(draft.learning_signals) == 1


def test_during_class_uses_complete_explanation_instruction():
    fake_client = FakeLLMClient()
    agent = RAGAnswerAgent(fake_client)

    agent.answer(
        question="อธิบาย gradient descent",
        phase=LearningPhase.DURING_CLASS,
        retrieved_chunks=[
            create_retrieved_chunk()
        ],
    )

    assert "DURING-CLASS" in fake_client.system_prompt
    assert (
        "complete explanation"
        in fake_client.system_prompt
    )


def test_after_class_uses_revision_instruction():
    fake_client = FakeLLMClient()
    agent = RAGAnswerAgent(fake_client)

    agent.answer(
        question="ทบทวน gradient descent",
        phase=LearningPhase.AFTER_CLASS,
        retrieved_chunks=[
            create_retrieved_chunk()
        ],
    )

    assert "AFTER-CLASS" in fake_client.system_prompt
    assert "support revision" in fake_client.system_prompt


def test_prompt_contains_verified_provenance():
    fake_client = FakeLLMClient()
    agent = RAGAnswerAgent(fake_client)

    draft = agent.answer(
        question="Gradient descent คืออะไร",
        phase=LearningPhase.DURING_CLASS,
        retrieved_chunks=[
            create_retrieved_chunk()
        ],
    )

    prompt = json.loads(fake_client.user_prompt)
    context = prompt["material_context"][0]

    assert context["chunk_id"] == "fused-gradient"
    assert context["source_chunk_ids"] == [
        "chunk-0002"
    ]
    assert context["asset_ids"] == [
        "asset-0002"
    ]
    assert context["page_number"] == 2
    assert context["chunk_type"] == "mixed"
    assert context["source_type"] == "mixed"
    assert context["retrieval_score"] == 0.90

    assert draft.grounded_chunk_ids == (
        "fused-gradient",
    )
    assert draft.grounded_source_chunk_ids == (
        "chunk-0002",
    )
    assert draft.grounded_asset_ids == (
        "asset-0002",
    )


def test_answer_rejects_empty_question():
    agent = RAGAnswerAgent(FakeLLMClient())

    with pytest.raises(
        RAGAnswerAgentError,
        match="question must not be empty",
    ):
        agent.answer(
            question="   ",
            phase=LearningPhase.PRE_CLASS,
            retrieved_chunks=[
                create_retrieved_chunk()
            ],
        )


def test_answer_rejects_empty_retrieval_context():
    agent = RAGAnswerAgent(FakeLLMClient())

    with pytest.raises(
        RAGAnswerAgentError,
        match="retrieved_chunks must not be empty",
    ):
        agent.answer(
            question="Gradient descent คืออะไร",
            phase=LearningPhase.PRE_CLASS,
            retrieved_chunks=[],
        )


def test_answer_rejects_invalid_confidence():
    fake_client = FakeLLMClient(
        {
            "answer": "Invalid confidence.",
            "confidence": 1.5,
            "learning_signals": [],
        }
    )

    agent = RAGAnswerAgent(fake_client)

    with pytest.raises(
        RAGAnswerAgentError,
        match="schema validation",
    ):
        agent.answer(
            question="Gradient descent คืออะไร",
            phase=LearningPhase.DURING_CLASS,
            retrieved_chunks=[
                create_retrieved_chunk()
            ],
        )


def test_answer_rejects_missing_answer():
    fake_client = FakeLLMClient(
        {
            "confidence": 0.8,
            "learning_signals": [],
        }
    )

    agent = RAGAnswerAgent(fake_client)

    with pytest.raises(
        RAGAnswerAgentError,
        match="schema validation",
    ):
        agent.answer(
            question="Gradient descent คืออะไร",
            phase=LearningPhase.DURING_CLASS,
            retrieved_chunks=[
                create_retrieved_chunk()
            ],
        )


def test_answer_rejects_model_generated_citations():
    fake_client = FakeLLMClient(
        {
            "answer": "Grounded answer.",
            "confidence": 0.8,
            "learning_signals": [],
            "citations": [
                {
                    "page_number": 999,
                    "chunk_id": "fabricated-chunk",
                }
            ],
        }
    )

    agent = RAGAnswerAgent(fake_client)

    with pytest.raises(
        RAGAnswerAgentError,
        match="schema validation",
    ):
        agent.answer(
            question="Gradient descent คืออะไร",
            phase=LearningPhase.DURING_CLASS,
            retrieved_chunks=[
                create_retrieved_chunk()
            ],
        )


def test_answer_rejects_duplicate_retrieved_chunk():
    retrieved = create_retrieved_chunk()

    agent = RAGAnswerAgent(FakeLLMClient())

    with pytest.raises(
        RAGAnswerAgentError,
        match="duplicate chunk_id",
    ):
        agent.answer(
            question="Gradient descent คืออะไร",
            phase=LearningPhase.DURING_CLASS,
            retrieved_chunks=[
                retrieved,
                retrieved,
            ],
        )


def test_answer_limits_material_context_size():
    fake_client = FakeLLMClient()

    agent = RAGAnswerAgent(
        fake_client,
        max_context_chars=20,
    )

    draft = agent.answer(
        question="Gradient descent คืออะไร",
        phase=LearningPhase.DURING_CLASS,
        retrieved_chunks=[
            create_retrieved_chunk(
                text="A" * 100
            )
        ],
    )

    prompt = json.loads(fake_client.user_prompt)
    context_text = (
        prompt["material_context"][0]["text"]
    )

    assert context_text == "A" * 20
    assert draft.grounded_chunk_ids == (
        "fused-gradient",
    )