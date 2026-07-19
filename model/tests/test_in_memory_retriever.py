from src.ingestion.pdf_ingestor import MaterialChunk
from src.retrieval.in_memory_retriever import InMemoryRetriever


def create_chunk(
    chunk_id: str,
    page: int,
    text: str,
) -> MaterialChunk:
    return MaterialChunk(
        chunk_id=chunk_id,
        material_id="material-001",
        material_name="lesson.pdf",
        page_number=page,
        chunk_index=0,
        text=text,
    )


def test_retriever_returns_most_relevant_chunk():
    chunks = [
        create_chunk(
            "chunk-gradient",
            2,
            "Gradient descent updates parameters to reduce loss.",
        ),
        create_chunk(
            "chunk-database",
            5,
            "A relational database stores data in tables.",
        ),
    ]

    retriever = InMemoryRetriever(chunks)

    results = retriever.search(
        "How does gradient descent reduce loss?",
        top_k=1,
    )

    assert len(results) == 1
    assert results[0].chunk.chunk_id == "chunk-gradient"
    assert results[0].chunk.page_number == 2
    assert results[0].score > 0