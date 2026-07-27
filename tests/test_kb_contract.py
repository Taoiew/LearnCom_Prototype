from schemas.kb_contract import EnrichedKnowledge, ReviewStatus


def test_enriched_knowledge_contract():
    knowledge = EnrichedKnowledge(
        knowledge_id="kb-001",
        material_id="material-001",
        source_chunk_ids=["chunk-001"],
        page_numbers=[1],
        topic="Gradient Descent",
        summary="วิธีปรับพารามิเตอร์เพื่อลดค่า loss",
        key_concepts=["gradient", "learning rate", "loss"],
        learning_objectives=[
            "อธิบายการปรับพารามิเตอร์ด้วย gradient ได้"
        ],
        common_misconceptions=[
            "learning rate สูงย่อมดีกว่าเสมอ"
        ],
        suggested_questions=[
            "learning rate ส่งผลต่อการเรียนรู้อย่างไร"
        ],
        source_quote=(
            "Gradient descent updates model parameters "
            "to reduce the loss."
        ),
        confidence=0.90,
        agent_model="mock-agent",
    )

    assert knowledge.review_status == ReviewStatus.PENDING
    assert knowledge.source_chunk_ids == ["chunk-001"]
    assert knowledge.page_numbers == [1]