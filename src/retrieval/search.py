"""Basic retrieval helpers."""

from typing import Iterable


class SimpleRetriever:
    """Very small retrieval component that filters documents by keyword."""

    def retrieve(self, documents: Iterable[str], query: str) -> list[str]:
        query_terms = set(query.lower().split())
        results: list[str] = []
        for document in documents:
            if query_terms and query_terms.issubset(set(document.lower().split())):
                results.append(document)
        return results
