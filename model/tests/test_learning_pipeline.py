from schemas.model_contract import (
    ChatRequest,
    LearningPhase,
    ScopeDecision,
)
from src.agents.answer_agent import AnswerDraft
from src.ingestion.pdf_ingestor import MaterialChunk
from src.retrieval.in_memory_retriever import InMemoryRetriever
from src.routing.scope_router import ScopeRouter
from src.service.learning_pipeline import LearningCompanionPipeline


class FakeAnswerAgent:
    def answer(
        self,
        question,
        phase,
        retrieved_chunks,
    ):
        return AnswerDraft(
            answer="Gradient descent ช่วยลดค่า loss",
            confidence=0.90,
            learning_signals=[],
        )
    
class FakeExternalAgent:
    def __init__(self):
        self.was_called = False

    def answer(
        self,
        question,
        phase,
        retrieved_chunks,
    ):
        self.was_called = True

        return AnswerDraft(
            answer=(
                "Momentum optimization ใช้ค่าการอัปเดตก่อนหน้า "
                "เพื่อช่วยปรับทิศทางการเรียนรู้"
            ),
            confidence=0.80,
            learning_signals=[],
        )


def create_pipeline() -> LearningCompanionPipeline:
    chunk = MaterialChunk(
        chunk_id="chunk-001",
        material_id="material-001",
        material_name="lesson.pdf",
        page_number=4,
        chunk_index=0,
        text=(
            "Gradient descent updates parameters "
            "to reduce loss."
        ),
    )

    return LearningCompanionPipeline(
        retriever=InMemoryRetriever([chunk]),
        scope_router=ScopeRouter(
            material_threshold=0.10,
            course_threshold=0.60,
        ),
        material_answer_agent=FakeAnswerAgent(),
    )


def create_request(question: str) -> ChatRequest:
    return ChatRequest(
        student_id="student-001",
        course_id="course-001",
        class_session_id="session-001",
        phase=LearningPhase.DURING_CLASS,
        question=question,
    )


def test_pipeline_returns_answer_with_material_citation():
    pipeline = create_pipeline()

    response = pipeline.run(
        create_request("How does gradient descent reduce loss?"),
        course_relevance_score=0.90,
    )

    assert response.scope == ScopeDecision.IN_MATERIAL
    assert response.citations[0].material_id == "material-001"
    assert response.citations[0].page_number == 4
    assert response.used_external_agent is False


def test_pipeline_rejects_unrelated_question():
    pipeline = create_pipeline()

    response = pipeline.run(
        create_request("วันนี้กินอะไรดี"),
        course_relevance_score=0.10,
    )

    assert response.scope == ScopeDecision.UNRELATED
    assert response.citations == []


def test_pipeline_handles_unsafe_question():
    pipeline = create_pipeline()

    response = pipeline.run(
        create_request("unsafe question"),
        course_relevance_score=0.90,
        unsafe=True,
    )

    assert response.scope == ScopeDecision.UNSAFE

def test_pipeline_uses_external_agent_for_course_question():
    chunk = MaterialChunk(
        chunk_id="chunk-001",
        material_id="material-001",
        material_name="lesson.pdf",
        page_number=4,
        chunk_index=0,
        text=(
            "Gradient descent updates parameters "
            "to reduce loss."
        ),
    )

    external_agent = FakeExternalAgent()

    pipeline = LearningCompanionPipeline(
        retriever=InMemoryRetriever([chunk]),
        scope_router=ScopeRouter(
            material_threshold=0.10,
            course_threshold=0.60,
        ),
        material_answer_agent=FakeAnswerAgent(),
        external_answer_agent=external_agent,
    )

    response = pipeline.run(
        create_request("What is momentum optimization?"),
        course_relevance_score=0.90,
    )

    assert (
        response.scope
        == ScopeDecision.COURSE_RELATED_OUTSIDE_MATERIAL
    )
    assert response.used_external_agent is True
    assert external_agent.was_called is True
    assert response.citations == []
    assert response.confidence == 0.80
class FakeRequestScopedRetriever:
    def __init__(self, results):
        self.results = results
        self.received_request = None

    def search_for(
        self,
        *,
        request,
        top_k=3,
    ):
        self.received_request = request
        return self.results


def test_pipeline_supports_request_scoped_retriever():
    from schemas.model_contract import (
        ChatRequest,
        LearningPhase,
    )
    from src.routing.scope_router import ScopeRouter
    from src.service.learning_pipeline import (
        LearningCompanionPipeline,
    )

    retriever = FakeRequestScopedRetriever([])

    pipeline = LearningCompanionPipeline(
        retriever=retriever,
        scope_router=ScopeRouter(
            material_threshold=0.1,
            course_threshold=0.6,
        ),
        material_answer_agent=None,
        top_k=3,
    )

    request = ChatRequest(
        student_id="student-one",
        course_id="CS242",
        class_session_id="week-07",
        phase=LearningPhase.DURING_CLASS,
        question="Question",
        conversation_id="conversation-one",
    )

    response = pipeline.run(
        request=request,
        course_relevance_score=0.0,
        unsafe=False,
    )

    assert retriever.received_request == request
    assert response.scope.value == "unrelated"