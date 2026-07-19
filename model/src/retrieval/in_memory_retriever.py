import re
from dataclasses import dataclass

from src.ingestion.pdf_ingestor import MaterialChunk


@dataclass(frozen=True)
class RetrievedChunk:
    chunk: MaterialChunk
    score: float


class InMemoryRetriever:
    def __init__(self, chunks: list[MaterialChunk]) -> None:
        self.chunks = chunks

    def search(
        self,
        query: str,
        top_k: int = 3,
    ) -> list[RetrievedChunk]:
        if top_k <= 0:
            raise ValueError("top_k must be greater than zero")

        results = [
            RetrievedChunk(
                chunk=chunk,
                score=self._similarity(query, chunk.text),
            )
            for chunk in self.chunks
        ]

        results = [
            result
            for result in results
            if result.score > 0
        ]

        return sorted(
            results,
            key=lambda result: result.score,
            reverse=True,
        )[:top_k]

    def best_score(self, query: str) -> float:
        results = self.search(query, top_k=1)
        return results[0].score if results else 0.0

    @classmethod
    def _similarity(cls, query: str, text: str) -> float:
        query_terms = cls._terms(query)
        text_terms = cls._terms(text)

        term_score = cls._jaccard(query_terms, text_terms)

        query_ngrams = cls._character_ngrams(query)
        text_ngrams = cls._character_ngrams(text)

        ngram_score = cls._jaccard(
            query_ngrams,
            text_ngrams,
        )

        return round(
            (term_score * 0.6) + (ngram_score * 0.4),
            4,
        )

    @staticmethod
    def _terms(text: str) -> set[str]:
        return set(
            re.findall(r"[\w\u0E00-\u0E7F]+", text.lower())
        )

    @staticmethod
    def _character_ngrams(
        text: str,
        size: int = 3,
    ) -> set[str]:
        normalized = re.sub(r"\s+", "", text.lower())

        if len(normalized) < size:
            return {normalized} if normalized else set()

        return {
            normalized[index:index + size]
            for index in range(len(normalized) - size + 1)
        }

    @staticmethod
    def _jaccard(
        first: set[str],
        second: set[str],
    ) -> float:
        if not first or not second:
            return 0.0

        return len(first & second) / len(first | second)