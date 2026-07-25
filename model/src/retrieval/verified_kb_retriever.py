from pathlib import Path
from threading import RLock

from src.retrieval.in_memory_retriever import (
    InMemoryRetriever,
)
from src.retrieval.verified_kb_loader import (
    LoadedVerifiedKB,
    VerifiedKBLoader,
)


class VerifiedKBRetriever(InMemoryRetriever):
    def __init__(
        self,
        verified_kb: LoadedVerifiedKB,
    ) -> None:
        self._lock = RLock()

        self._verified_kbs: dict[
            str,
            LoadedVerifiedKB,
        ] = {
            verified_kb.material_id: verified_kb
        }

        # เก็บไว้เพื่อให้โค้ดเดิมที่อ้าง
        # retriever.verified_kb ยังใช้ได้
        self.verified_kb = verified_kb

        super().__init__(
            chunks=verified_kb.to_material_chunks()
        )

    @classmethod
    def from_file(
        cls,
        verified_kb_path: str | Path,
    ) -> "VerifiedKBRetriever":
        verified_kb = VerifiedKBLoader().load(
            verified_kb_path
        )

        return cls(verified_kb)

    def activate_file(
        self,
        verified_kb_path: str | Path,
    ) -> LoadedVerifiedKB:
        verified_kb = VerifiedKBLoader().load(
            verified_kb_path
        )

        self.activate(verified_kb)

        return verified_kb

    def activate(
        self,
        verified_kb: LoadedVerifiedKB,
    ) -> None:
        with self._lock:
            self._verified_kbs[
                verified_kb.material_id
            ] = verified_kb

            self.verified_kb = verified_kb
            self.chunks = self._build_chunks()

    def deactivate(
        self,
        material_id: str,
    ) -> bool:
        normalized_material_id = material_id.strip()

        if not normalized_material_id:
            raise ValueError(
                "material_id must not be empty"
            )

        with self._lock:
            if (
                normalized_material_id
                not in self._verified_kbs
            ):
                return False

            del self._verified_kbs[
                normalized_material_id
            ]

            self.chunks = self._build_chunks()

            if self._verified_kbs:
                self.verified_kb = next(
                    reversed(
                        self._verified_kbs.values()
                    )
                )

            return True

    def active_material_ids(
        self,
    ) -> tuple[str, ...]:
        with self._lock:
            return tuple(
                sorted(self._verified_kbs)
            )

    def _build_chunks(
        self,
    ) -> list:
        chunks = []

        for material_id in sorted(
            self._verified_kbs
        ):
            verified_kb = self._verified_kbs[
                material_id
            ]

            chunks.extend(
                verified_kb.to_material_chunks()
            )

        return chunks