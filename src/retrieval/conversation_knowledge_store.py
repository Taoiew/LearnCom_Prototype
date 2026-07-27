from pathlib import Path
from threading import RLock

from src.retrieval.verified_kb_retriever import (
    VerifiedKBRetriever,
)


class ConversationKnowledgeStore:
    """
    Temporary knowledge store for student chat attachments.

    Knowledge is isolated by:
    - student_id
    - conversation_id

    Instructor course materials must not be stored here.
    """

    def __init__(self) -> None:
        self._lock = RLock()

        self._retrievers: dict[
            tuple[str, str],
            VerifiedKBRetriever,
        ] = {}

    def activate_attachment(
        self,
        *,
        student_id: str,
        conversation_id: str,
        verified_kb_path: str | Path,
    ) -> str:
        normalized_student_id = self._normalize_required(
            student_id,
            "student_id",
        )
        normalized_conversation_id = (
            self._normalize_required(
                conversation_id,
                "conversation_id",
            )
        )

        path = Path(verified_kb_path)

        if not path.is_file():
            raise FileNotFoundError(
                f"Verified KB not found: {path}"
            )

        key = (
            normalized_student_id,
            normalized_conversation_id,
        )

        with self._lock:
            retriever = self._retrievers.get(key)

            if retriever is None:
                retriever = VerifiedKBRetriever.from_file(
                    path
                )
                self._retrievers[key] = retriever

                return retriever.verified_kb.material_id

            loaded_kb = retriever.activate_file(path)

            return loaded_kb.material_id

    def get_retriever(
        self,
        *,
        student_id: str,
        conversation_id: str,
    ) -> VerifiedKBRetriever | None:
        key = (
            self._normalize_required(
                student_id,
                "student_id",
            ),
            self._normalize_required(
                conversation_id,
                "conversation_id",
            ),
        )

        with self._lock:
            return self._retrievers.get(key)

    def search(
        self,
        *,
        student_id: str,
        conversation_id: str,
        query: str,
        top_k: int = 3,
    ):
        if top_k < 1:
            raise ValueError(
                "top_k must be at least 1"
            )

        retriever = self.get_retriever(
            student_id=student_id,
            conversation_id=conversation_id,
        )

        if retriever is None:
            return []

        return retriever.search(
            query=query,
            top_k=top_k,
        )

    def active_attachment_ids(
        self,
        *,
        student_id: str,
        conversation_id: str,
    ) -> tuple[str, ...]:
        retriever = self.get_retriever(
            student_id=student_id,
            conversation_id=conversation_id,
        )

        if retriever is None:
            return ()

        return retriever.active_material_ids()

    def remove_attachment(
        self,
        *,
        student_id: str,
        conversation_id: str,
        material_id: str,
    ) -> bool:
        retriever = self.get_retriever(
            student_id=student_id,
            conversation_id=conversation_id,
        )

        if retriever is None:
            return False

        return retriever.deactivate(material_id)

    def clear_conversation(
        self,
        *,
        student_id: str,
        conversation_id: str,
    ) -> bool:
        key = (
            self._normalize_required(
                student_id,
                "student_id",
            ),
            self._normalize_required(
                conversation_id,
                "conversation_id",
            ),
        )

        with self._lock:
            return self._retrievers.pop(
                key,
                None,
            ) is not None

    @staticmethod
    def _normalize_required(
        value: str,
        field_name: str,
    ) -> str:
        normalized = value.strip()

        if not normalized:
            raise ValueError(
                f"{field_name} must not be empty"
            )

        return normalized