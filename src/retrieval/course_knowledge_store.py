from pathlib import Path
from threading import RLock

from src.retrieval.verified_kb_retriever import (
    VerifiedKBRetriever,
)


class CourseKnowledgeStore:
    """
    Persistent knowledge store for instructor materials.

    Knowledge is isolated by:
    - course_id
    - class_session_id

    Student chat attachments must not be activated here.
    """

    def __init__(self) -> None:
        self._lock = RLock()

        self._retrievers: dict[
            tuple[str, str],
            VerifiedKBRetriever,
        ] = {}

    def activate(
        self,
        *,
        course_id: str,
        class_session_id: str,
        verified_kb_path: str | Path,
    ) -> str:
        """
        Activate an instructor Verified KB artifact.

        If the course/session already has a retriever,
        the new material is added to that retriever.

        If the same material_id already exists,
        VerifiedKBRetriever.activate_file() replaces it.
        """
        normalized_course_id = self._normalize_required(
            course_id,
            "course_id",
        )
        normalized_session_id = self._normalize_required(
            class_session_id,
            "class_session_id",
        )

        path = Path(verified_kb_path)

        if not path.is_file():
            raise FileNotFoundError(
                f"Verified KB not found: {path}"
            )

        key = (
            normalized_course_id,
            normalized_session_id,
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
        course_id: str,
        class_session_id: str,
    ) -> VerifiedKBRetriever | None:
        normalized_course_id = self._normalize_required(
            course_id,
            "course_id",
        )
        normalized_session_id = self._normalize_required(
            class_session_id,
            "class_session_id",
        )

        key = (
            normalized_course_id,
            normalized_session_id,
        )

        with self._lock:
            return self._retrievers.get(key)

    def search(
        self,
        *,
        course_id: str,
        class_session_id: str,
        query: str,
        top_k: int = 3,
    ):
        """
        Search only instructor materials belonging to the
        requested course and class session.
        """
        if top_k < 1:
            raise ValueError(
                "top_k must be at least 1"
            )

        retriever = self.get_retriever(
            course_id=course_id,
            class_session_id=class_session_id,
        )

        if retriever is None:
            return []

        return retriever.search(
            query=query,
            top_k=top_k,
        )

    def deactivate_material(
        self,
        *,
        course_id: str,
        class_session_id: str,
        material_id: str,
    ) -> bool:
        retriever = self.get_retriever(
            course_id=course_id,
            class_session_id=class_session_id,
        )

        if retriever is None:
            return False

        return retriever.deactivate(material_id)

    def active_material_ids(
        self,
        *,
        course_id: str,
        class_session_id: str,
    ) -> tuple[str, ...]:
        retriever = self.get_retriever(
            course_id=course_id,
            class_session_id=class_session_id,
        )

        if retriever is None:
            return ()

        return retriever.active_material_ids()

    def remove_session(
        self,
        *,
        course_id: str,
        class_session_id: str,
    ) -> bool:
        """
        Remove all active instructor knowledge for one session.
        """
        normalized_course_id = self._normalize_required(
            course_id,
            "course_id",
        )
        normalized_session_id = self._normalize_required(
            class_session_id,
            "class_session_id",
        )

        key = (
            normalized_course_id,
            normalized_session_id,
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