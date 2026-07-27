import pytest

from src.ingestion.pdf_ingestor import MaterialChunk
from src.retrieval.in_memory_retriever import (
    InMemoryRetriever,
)


def create_chunk(
    chunk_id: str,
    page: int,
    text: str,
    *,
    chunk_index: int = 0,
) -> MaterialChunk:
    return MaterialChunk(
        chunk_id=chunk_id,
        material_id="material-001",
        material_name="lesson.pdf",
        page_number=page,
        chunk_index=chunk_index,
        text=text,
    )


def test_retriever_returns_most_relevant_chunk() -> None:
    chunks = [
        create_chunk(
            "chunk-gradient",
            2,
            (
                "Gradient descent updates parameters "
                "to reduce loss."
            ),
        ),
        create_chunk(
            "chunk-database",
            5,
            (
                "A relational database stores data "
                "in tables."
            ),
        ),
    ]

    retriever = InMemoryRetriever(chunks)

    results = retriever.search(
        "How does gradient descent reduce loss?",
        top_k=1,
    )

    assert len(results) == 1
    assert (
        results[0].chunk.chunk_id
        == "chunk-gradient"
    )
    assert results[0].chunk.page_number == 2
    assert results[0].score > 0.10


def test_long_verified_kb_content_is_not_penalized() -> None:
    long_context = " ".join(
        [
            (
                "The Inventory class contains methods "
                "for managing products and quantities."
            )
        ]
        * 50
    )

    chunk = create_chunk(
        "fused-inventory",
        2,
        (
            "Custom Exceptions Required: "
            "ProductExistsError, "
            "ProductNotFoundError, "
            "InvalidStockError, and "
            "CorruptedInventoryFileError inherit "
            "from Exception. "
            + long_context
        ),
    )

    retriever = InMemoryRetriever([chunk])

    score = retriever.best_score(
        (
            "What custom exceptions are required, "
            "and how are they related to Exception?"
        )
    )

    assert score >= 0.10


def test_plural_and_singular_terms_match() -> None:
    retriever = InMemoryRetriever(
        [
            create_chunk(
                "chunk-exception",
                2,
                (
                    "Each custom exception inherits "
                    "from Exception."
                ),
            )
        ]
    )

    results = retriever.search(
        "custom exceptions",
        top_k=1,
    )

    assert len(results) == 1
    assert results[0].score > 0.50


def test_stop_words_do_not_dominate_score() -> None:
    relevant = create_chunk(
        "chunk-relevant",
        2,
        (
            "ProductExistsError inherits "
            "from Exception."
        ),
    )

    unrelated = create_chunk(
        "chunk-unrelated",
        3,
        (
            "The system is in the classroom "
            "and it is ready."
        ),
    )

    retriever = InMemoryRetriever(
        [unrelated, relevant]
    )

    results = retriever.search(
        (
            "What is the ProductExistsError "
            "and how is it related to Exception?"
        ),
        top_k=1,
    )

    assert (
        results[0].chunk.chunk_id
        == "chunk-relevant"
    )


def test_thai_query_matches_thai_material() -> None:
    retriever = InMemoryRetriever(
        [
            create_chunk(
                "chunk-thai",
                4,
                (
                    "ระบบตรวจสอบข้อมูลก่อนบันทึก "
                    "และแจ้งข้อผิดพลาดเมื่อข้อมูลไม่ถูกต้อง"
                ),
            ),
            create_chunk(
                "chunk-english",
                5,
                "A database stores product records.",
            ),
        ]
    )

    results = retriever.search(
        "ระบบตรวจสอบข้อมูลทำงานอย่างไร",
        top_k=1,
    )

    assert len(results) == 1
    assert (
        results[0].chunk.chunk_id
        == "chunk-thai"
    )
    assert results[0].score > 0


def test_empty_query_returns_no_results() -> None:
    retriever = InMemoryRetriever(
        [
            create_chunk(
                "chunk-001",
                1,
                "Some learning material.",
            )
        ]
    )

    assert retriever.search("   ") == []
    assert retriever.best_score("") == 0.0


def test_search_rejects_invalid_top_k() -> None:
    retriever = InMemoryRetriever([])

    with pytest.raises(
        ValueError,
        match="top_k must be greater than zero",
    ):
        retriever.search(
            "inventory",
            top_k=0,
        )


def test_retriever_rejects_duplicate_chunk_ids() -> None:
    chunks = [
        create_chunk(
            "duplicate-chunk",
            1,
            "First content.",
        ),
        create_chunk(
            "duplicate-chunk",
            2,
            "Second content.",
        ),
    ]

    with pytest.raises(
        ValueError,
        match="duplicate chunk_id",
    ):
        InMemoryRetriever(chunks)


def test_results_have_deterministic_order() -> None:
    chunks = [
        create_chunk(
            "chunk-page-3",
            3,
            "Inventory exception.",
        ),
        create_chunk(
            "chunk-page-2-b",
            2,
            "Inventory exception.",
            chunk_index=1,
        ),
        create_chunk(
            "chunk-page-2-a",
            2,
            "Inventory exception.",
            chunk_index=0,
        ),
    ]

    retriever = InMemoryRetriever(chunks)

    results = retriever.search(
        "inventory exception",
        top_k=3,
    )

    assert [
        result.chunk.chunk_id
        for result in results
    ] == [
        "chunk-page-2-a",
        "chunk-page-2-b",
        "chunk-page-3",
    ]


def test_top_k_limits_number_of_results() -> None:
    retriever = InMemoryRetriever(
        [
            create_chunk(
                "chunk-001",
                1,
                "Inventory exception one.",
            ),
            create_chunk(
                "chunk-002",
                2,
                "Inventory exception two.",
            ),
            create_chunk(
                "chunk-003",
                3,
                "Inventory exception three.",
            ),
        ]
    )

    results = retriever.search(
        "inventory exception",
        top_k=2,
    )

    assert len(results) == 2
    assert all(
        result.score > 0
        for result in results
    )