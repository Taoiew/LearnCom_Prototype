from schemas.kb_contract import EnrichedKnowledge, ReviewStatus
from src.evaluation.kb_verifier import KBVerifier
from src.ingestion.pdf_ingestor import MaterialChunk


def create_chunk() -> MaterialChunk:
    return MaterialChunk(
        chunk_id="chunk-001",
        material_id="material-001",
        material_name="lesson.pdf",
        page_number=3,
        chunk_index=0,
        text="Gradient descent updates parameters to reduce loss.",
    )


def create_knowledge(source_quote: str) -> EnrichedKnowledge:
    return EnrichedKnowledge(
        knowledge_id="kb-001",
        material_id="material-001",
        source_chunk_ids=["chunk-001"],
        page_numbers=[3],
        topic="Gradient Descent",
        summary="วิธีปรับพารามิเตอร์เพื่อลด loss",
        source_quote=source_quote,
        confidence=0.90,
        agent_model="test-agent",
    )


def test_verifier_accepts_grounded_knowledge():
    chunk = create_chunk()
    knowledge = create_knowledge(
        "Gradient descent updates parameters"
    )

    result = KBVerifier().verify(knowledge, [chunk])

    assert result.is_verified is True
    assert result.reasons == []
    assert result.knowledge.review_status == ReviewStatus.VERIFIED


def test_verifier_rejects_unsupported_quote():
    chunk = create_chunk()
    knowledge = create_knowledge(
        "Gradient descent always finds the perfect solution."
    )

    result = KBVerifier().verify(knowledge, [chunk])

    assert result.is_verified is False
    assert result.reasons
    assert result.knowledge.review_status == ReviewStatus.REJECTED