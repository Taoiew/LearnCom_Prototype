from pathlib import Path

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