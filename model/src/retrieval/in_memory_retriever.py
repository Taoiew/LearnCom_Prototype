import re
import unicodedata
from dataclasses import dataclass

from src.ingestion.pdf_ingestor import MaterialChunk


@dataclass(frozen=True)
class RetrievedChunk:
    chunk: MaterialChunk
    score: float


class InMemoryRetriever:
    """
    Lightweight lexical retriever for the prototype runtime.

    The score combines:

    - query term coverage;
    - term-set similarity;
    - character n-gram coverage.

    Query coverage receives the highest weight so that a long Verified KB
    record does not receive an artificially low score merely because it
    contains substantially more text than the student's question.
    """

    TERM_COVERAGE_WEIGHT = 0.70
    TERM_JACCARD_WEIGHT = 0.15
    NGRAM_COVERAGE_WEIGHT = 0.15

    _ENGLISH_STOP_WORDS = frozenset(
        {
            "a",
            "an",
            "and",
            "are",
            "as",
            "at",
            "be",
            "by",
            "do",
            "does",
            "for",
            "from",
            "how",
            "in",
            "is",
            "it",
            "of",
            "on",
            "or",
            "that",
            "the",
            "their",
            "them",
            "they",
            "this",
            "to",
            "was",
            "were",
            "what",
            "when",
            "where",
            "which",
            "who",
            "why",
            "with",
        }
    )

    def __init__(
        self,
        chunks: list[MaterialChunk],
    ) -> None:
        chunk_ids = [
            chunk.chunk_id
            for chunk in chunks
        ]

        if len(chunk_ids) != len(set(chunk_ids)):
            raise ValueError(
                "Retriever chunks contain duplicate chunk_id"
            )

        self.chunks = list(chunks)

    def search(
        self,
        query: str,
        top_k: int = 3,
    ) -> list[RetrievedChunk]:
        if top_k <= 0:
            raise ValueError(
                "top_k must be greater than zero"
            )

        normalized_query = self._normalize_text(query)

        if not normalized_query:
            return []

        results = [
            RetrievedChunk(
                chunk=chunk,
                score=self._similarity(
                    normalized_query,
                    chunk.text,
                ),
            )
            for chunk in self.chunks
        ]

        positive_results = [
            result
            for result in results
            if result.score > 0
        ]

        return sorted(
            positive_results,
            key=lambda result: (
                -result.score,
                result.chunk.page_number,
                result.chunk.chunk_index,
                result.chunk.chunk_id,
            ),
        )[:top_k]

    def best_score(
        self,
        query: str,
    ) -> float:
        results = self.search(
            query=query,
            top_k=1,
        )

        return (
            results[0].score
            if results
            else 0.0
        )

    @classmethod
    def _similarity(
        cls,
        query: str,
        text: str,
    ) -> float:
        normalized_query = cls._normalize_text(query)
        normalized_text = cls._normalize_text(text)

        if not normalized_query or not normalized_text:
            return 0.0

        query_terms = cls._terms(normalized_query)
        text_terms = cls._terms(normalized_text)

        term_coverage_score = cls._coverage(
            expected=query_terms,
            available=text_terms,
        )

        term_jaccard_score = cls._jaccard(
            query_terms,
            text_terms,
        )

        query_ngrams = cls._character_ngrams(
            normalized_query,
        )
        text_ngrams = cls._character_ngrams(
            normalized_text,
        )

        ngram_coverage_score = cls._coverage(
            expected=query_ngrams,
            available=text_ngrams,
        )

        score = (
            term_coverage_score
            * cls.TERM_COVERAGE_WEIGHT
            + term_jaccard_score
            * cls.TERM_JACCARD_WEIGHT
            + ngram_coverage_score
            * cls.NGRAM_COVERAGE_WEIGHT
        )

        return round(
            min(max(score, 0.0), 1.0),
            4,
        )

    @classmethod
    def _terms(
        cls,
        text: str,
    ) -> set[str]:
        raw_terms = re.findall(
            r"[\w\u0E00-\u0E7F]+",
            cls._normalize_text(text),
        )

        normalized_terms = {
            cls._normalize_term(term)
            for term in raw_terms
        }

        return {
            term
            for term in normalized_terms
            if (
                term
                and term
                not in cls._ENGLISH_STOP_WORDS
            )
        }

    @staticmethod
    def _normalize_text(
        text: str,
    ) -> str:
        normalized = unicodedata.normalize(
            "NFKC",
            text,
        )

        normalized = normalized.casefold()

        return re.sub(
            r"\s+",
            " ",
            normalized,
        ).strip()

    @staticmethod
    def _normalize_term(
        term: str,
    ) -> str:
        normalized = term.casefold().strip("_")

        if len(normalized) <= 3:
            return normalized

        # Lightweight English normalization for retrieval.
        # This intentionally avoids aggressive stemming.
        if (
            normalized.endswith("ies")
            and len(normalized) > 4
        ):
            return normalized[:-3] + "y"

        if (
            normalized.endswith("es")
            and len(normalized) > 4
        ):
            stem = normalized[:-2]

            if normalized.endswith(
                (
                    "ses",
                    "xes",
                    "zes",
                    "ches",
                    "shes",
                )
            ):
                return stem

        if (
            normalized.endswith("s")
            and not normalized.endswith("ss")
            and len(normalized) > 4
        ):
            return normalized[:-1]

        return normalized

    @classmethod
    def _character_ngrams(
        cls,
        text: str,
        size: int = 3,
    ) -> set[str]:
        if size <= 0:
            raise ValueError(
                "ngram size must be greater than zero"
            )

        normalized = re.sub(
            r"[^\w\u0E00-\u0E7F]+",
            "",
            cls._normalize_text(text),
        )

        if not normalized:
            return set()

        if len(normalized) < size:
            return {normalized}

        return {
            normalized[index:index + size]
            for index in range(
                len(normalized) - size + 1
            )
        }

    @staticmethod
    def _coverage(
        expected: set[str],
        available: set[str],
    ) -> float:
        if not expected or not available:
            return 0.0

        return len(
            expected & available
        ) / len(expected)

    @staticmethod
    def _jaccard(
        first: set[str],
        second: set[str],
    ) -> float:
        if not first or not second:
            return 0.0

        return len(
            first & second
        ) / len(
            first | second
        )