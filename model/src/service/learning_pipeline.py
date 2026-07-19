from typing import Protocol

from schemas.model_contract import (
    ChatRequest,
    ChatResponse,
    Citation,
    LearningPhase,
    ScopeDecision,
)
from src.agents.answer_agent import AnswerDraft
from src.retrieval.in_memory_retriever import (
    InMemoryRetriever,
    RetrievedChunk,
)
from src.routing.scope_router import RoutingInput, ScopeRouter


class AnswerProvider(Protocol):
    def answer(
        self,
        question: str,
        phase: LearningPhase,
        retrieved_chunks: list[RetrievedChunk],
    ) -> AnswerDraft:
        ...


class LearningCompanionPipeline:
    def __init__(
        self,
        retriever: InMemoryRetriever,
        scope_router: ScopeRouter,
        material_answer_agent: AnswerProvider,
        external_answer_agent: AnswerProvider | None = None,
        top_k: int = 3,
    ) -> None:
        self.retriever = retriever
        self.scope_router = scope_router
        self.material_answer_agent = material_answer_agent
        self.external_answer_agent = external_answer_agent
        self.top_k = top_k

    def run(
        self,
        request: ChatRequest,
        course_relevance_score: float,
        unsafe: bool = False,
    ) -> ChatResponse:
        retrieved = self.retriever.search(
            request.question,
            top_k=self.top_k,
        )

        material_score = (
            retrieved[0].score
            if retrieved
            else 0.0
        )

        routing = self.scope_router.route(
            RoutingInput(
                question=request.question,
                material_score=material_score,
                course_relevance_score=course_relevance_score,
                unsafe=unsafe,
            )
        )

        if routing.decision == ScopeDecision.UNSAFE:
            return ChatResponse(
                answer=(
                    "ฉันไม่สามารถช่วยตอบคำถามนี้ได้ "
                    "แต่สามารถช่วยในหัวข้อการเรียนที่ปลอดภัยได้"
                ),
                scope=routing.decision,
                confidence=1.0,
            )

        if routing.decision == ScopeDecision.UNRELATED:
            return ChatResponse(
                answer=(
                    "คำถามนี้อยู่นอกขอบเขตของวิชา "
                    "ลองถามเกี่ยวกับเนื้อหาในคาบเรียนนี้ได้"
                ),
                scope=routing.decision,
                confidence=1.0,
            )

        used_external_agent = False
        answer_agent = self.material_answer_agent

        if (
            routing.decision
            == ScopeDecision.COURSE_RELATED_OUTSIDE_MATERIAL
        ):
            if self.external_answer_agent is None:
                return ChatResponse(
                    answer=(
                        "คำถามนี้เกี่ยวข้องกับวิชา แต่ Material "
                        "ที่มีอยู่ยังไม่เพียงพอสำหรับคำตอบที่เชื่อถือได้"
                    ),
                    scope=routing.decision,
                    confidence=0.0,
                )

            answer_agent = self.external_answer_agent
            used_external_agent = True

        draft = answer_agent.answer(
            question=request.question,
            phase=request.phase,
            retrieved_chunks=retrieved,
        )

        citations = (
            self._create_citations(retrieved)
            if routing.decision == ScopeDecision.IN_MATERIAL
            else []
        )

        return ChatResponse(
            answer=draft.answer,
            scope=routing.decision,
            citations=citations,
            learning_signals=draft.learning_signals,
            used_external_agent=used_external_agent,
            confidence=draft.confidence,
        )

    @staticmethod
    def _create_citations(
        retrieved: list[RetrievedChunk],
    ) -> list[Citation]:
        return [
            Citation(
                material_id=result.chunk.material_id,
                material_name=result.chunk.material_name,
                chunk_id=result.chunk.chunk_id,
                page_number=result.chunk.page_number,
                quote=result.chunk.text[:300],
                relevance_score=result.score,
            )
            for result in retrieved
        ]