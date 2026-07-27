from dataclasses import dataclass

from schemas.model_contract import (
    ChatRequest,
    LearningPhase,
)
from src.ingestion.pdf_ingestor import (
    MaterialChunk,
)
from src.retrieval.in_memory_retriever import (
    RetrievedChunk,
)
from src.retrieval.merged_knowledge_retriever import (
    MergedKnowledgeRetriever,
)


@dataclass
class FakeCourseStore:
    results: list[RetrievedChunk]

    def search(
        self,
        **kwargs,
    ) -> list[RetrievedChunk]:
        return self.results


@dataclass
class FakeConversationStore:
    results: list[RetrievedChunk]

    def search(
        self,
        **kwargs,
    ) -> list[RetrievedChunk]:
        return self.results


def _result(
    *,
    chunk_id: str,
    material_id: str,
    score: float,
) -> RetrievedChunk:
    return RetrievedChunk(
        chunk=MaterialChunk(
            chunk_id=chunk_id,
            material_id=material_id,
            material_name=f"{material_id}.pdf",
            page_number=1,
            chunk_index=0,
            text=f"content for {chunk_id}",
        ),
        score=score,
    )


def test_merged_retriever_combines_and_ranks() -> None:
    course_result = _result(
        chunk_id="course-chunk",
        material_id="course-material",
        score=0.4,
    )

    attachment_result = _result(
        chunk_id="attachment-chunk",
        material_id="attachment-material",
        score=0.8,
    )

    retriever = MergedKnowledgeRetriever(
        course_store=FakeCourseStore(
            [course_result]
        ),
        conversation_store=(
            FakeConversationStore(
                [attachment_result]
            )
        ),
    )

    request = ChatRequest(
        student_id="student-one",
        course_id="CS242",
        class_session_id="week-07",
        phase=LearningPhase.DURING_CLASS,
        question="What is shown?",
        conversation_id="conversation-one",
    )

    results = retriever.search_for(
        request=request,
        top_k=3,
    )

    assert len(results) == 2
    assert (
        results[0].chunk.chunk_id
        == "attachment-chunk"
    )
    assert (
        results[1].chunk.chunk_id
        == "course-chunk"
    )


def test_request_without_conversation_uses_course_only() -> None:
    course_result = _result(
        chunk_id="course-chunk",
        material_id="course-material",
        score=0.5,
    )

    retriever = MergedKnowledgeRetriever(
        course_store=FakeCourseStore(
            [course_result]
        ),
        conversation_store=(
            FakeConversationStore(
                [
                    _result(
                        chunk_id="attachment-chunk",
                        material_id="attachment",
                        score=1.0,
                    )
                ]
            )
        ),
    )

    request = ChatRequest(
        student_id="student-one",
        course_id="CS242",
        class_session_id="week-07",
        phase=LearningPhase.DURING_CLASS,
        question="Explain this",
        conversation_id=None,
    )

    results = retriever.search_for(
        request=request,
        top_k=3,
    )

    assert len(results) == 1
    assert (
        results[0].chunk.chunk_id
        == "course-chunk"
    )