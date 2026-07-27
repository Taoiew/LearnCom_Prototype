from src.agents.kb_enrichment_agent import LLMKBEnrichmentAgent
from src.evaluation.kb_verifier import KBVerifier
from src.ingestion.pdf_ingestor import MaterialChunk


class FakeLLMClient:
    def chat_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
    ):
        return {
            "topic": "Gradient Descent",
            "summary": "วิธีปรับพารามิเตอร์เพื่อลด loss",
            "key_concepts": ["gradient", "loss"],
            "learning_objectives": [
                "อธิบายการปรับพารามิเตอร์ได้"
            ],
            "common_misconceptions": [],
            "suggested_questions": [
                "gradient descent ลด loss ได้อย่างไร"
            ],
            "source_quote": (
                "Gradient descent updates model parameters"
            ),
            "confidence": 0.90,
        }


def test_llm_kb_agent_and_verifier():
    chunk = MaterialChunk(
        chunk_id="chunk-001",
        material_id="material-001",
        material_name="lesson.pdf",
        page_number=2,
        chunk_index=0,
        text=(
            "Gradient descent updates model parameters "
            "to reduce the loss."
        ),
    )

    agent = LLMKBEnrichmentAgent(
        llm_client=FakeLLMClient(),
        agent_model="fake-model",
    )

    knowledge = agent.enrich(chunk)
    verification = KBVerifier().verify(knowledge, [chunk])

    assert knowledge.topic == "Gradient Descent"
    assert knowledge.source_chunk_ids == ["chunk-001"]
    assert verification.is_verified is True