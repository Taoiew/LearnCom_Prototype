from schemas.model_contract import LearningPhase
from src.agents.answer_agent import RAGAnswerAgent
from src.ingestion.pdf_ingestor import MaterialChunk
from src.retrieval.in_memory_retriever import RetrievedChunk


class FakeLLMClient:
    def __init__(self):
        self.system_prompt = ""

    def chat_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
    ):
        self.system_prompt = system_prompt

        return {
            "answer": "ลองอธิบายความหมายของ gradient ก่อน",
            "confidence": 0.85,
            "learning_signals": [
                {
                    "topic": "Gradient Descent",
                    "signal_type": "readiness_gap",
                    "severity": 0.40,
                    "explanation": "ยังไม่แน่ใจเรื่อง gradient",
                }
            ],
        }


def test_pre_class_answer_uses_readiness_instruction():
    chunk = MaterialChunk(
        chunk_id="chunk-001",
        material_id="material-001",
        material_name="lesson.pdf",
        page_number=2,
        chunk_index=0,
        text="Gradient descent updates parameters.",
    )

    retrieved = RetrievedChunk(
        chunk=chunk,
        score=0.90,
    )

    fake_client = FakeLLMClient()
    agent = RAGAnswerAgent(fake_client)

    draft = agent.answer(
        question="Gradient descent คืออะไร",
        phase=LearningPhase.PRE_CLASS,
        retrieved_chunks=[retrieved],
    )

    assert "PRE-CLASS" in fake_client.system_prompt
    assert "Do not reveal the complete answer" in fake_client.system_prompt
    assert draft.confidence == 0.85
    assert len(draft.learning_signals) == 1