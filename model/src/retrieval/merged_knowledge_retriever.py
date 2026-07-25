from schemas.model_contract import ChatRequest
from src.retrieval.conversation_knowledge_store import (
    ConversationKnowledgeStore,
)
from src.retrieval.course_knowledge_store import (
    CourseKnowledgeStore,
)
from src.retrieval.in_memory_retriever import (
    RetrievedChunk,
)


class MergedKnowledgeRetriever:
    """
    Request-scoped retriever.

    Instructor materials are searched by:
    - course_id
    - class_session_id

    Student attachments are searched by:
    - student_id
    - conversation_id

    Results are merged only for the current request.
    """

    def __init__(
        self,
        *,
        course_store: CourseKnowledgeStore,
        conversation_store: ConversationKnowledgeStore,
    ) -> None:
        self.course_store = course_store
        self.conversation_store = conversation_store

    def search_for(
        self,
        *,
        request: ChatRequest,
        top_k: int = 3,
    ) -> list[RetrievedChunk]:
        if top_k < 1:
            raise ValueError(
                "top_k must be at least 1"
            )

        course_results = self.course_store.search(
            course_id=request.course_id,
            class_session_id=request.class_session_id,
            query=request.question,
            top_k=top_k,
        )

        conversation_results: list[
            RetrievedChunk
        ] = []

        if request.conversation_id:
            conversation_results = (
                self.conversation_store.search(
                    student_id=request.student_id,
                    conversation_id=(
                        request.conversation_id
                    ),
                    query=request.question,
                    top_k=top_k,
                )
            )

        return self._merge_results(
            course_results=course_results,
            conversation_results=(
                conversation_results
            ),
            top_k=top_k,
        )

    @staticmethod
    def _merge_results(
        *,
        course_results: list[RetrievedChunk],
        conversation_results: list[
            RetrievedChunk
        ],
        top_k: int,
    ) -> list[RetrievedChunk]:
        best_by_chunk_id: dict[
            str,
            RetrievedChunk,
        ] = {}

        for result in (
            course_results
            + conversation_results
        ):
            chunk_id = result.chunk.chunk_id
            current = best_by_chunk_id.get(
                chunk_id
            )

            if (
                current is None
                or result.score > current.score
            ):
                best_by_chunk_id[
                    chunk_id
                ] = result

        ordered = sorted(
            best_by_chunk_id.values(),
            key=lambda result: (
                -result.score,
                result.chunk.material_id,
                result.chunk.page_number,
                result.chunk.chunk_index,
                result.chunk.chunk_id,
            ),
        )

        return ordered[:top_k]