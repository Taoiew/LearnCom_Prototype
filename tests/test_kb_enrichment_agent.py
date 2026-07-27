from schemas.kb_contract import ReviewStatus
from src.agents.kb_enrichment_agent import MockKBEnrichmentAgent
from src.ingestion.pdf_ingestor import MaterialChunk


def test_mock_kb_enrichment_agent():
    chunk = MaterialChunk(
        chunk_id="chunk-001",
        material_id="material-001",
        material_name="lesson.pdf",
        page_number=3,
        chunk_index=0,
        text=(
            "Gradient descent updates model parameters "
            "to reduce the loss."
        ),
    )

    agent = MockKBEnrichmentAgent()
    knowledge = agent.enrich(chunk)

    assert knowledge.material_id == "material-001"
    assert knowledge.source_chunk_ids == ["chunk-001"]
    assert knowledge.page_numbers == [3]
    assert knowledge.source_quote in chunk.text
    assert knowledge.review_status == ReviewStatus.PENDING
    assert knowledge.agent_model == "mock-agent"