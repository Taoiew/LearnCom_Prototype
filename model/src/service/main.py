from schemas.model_contract import LearningPhase
from src.agents.answer_agent import AnswerDraft
from src.ingestion.pdf_ingestor import MaterialChunk
from src.retrieval.in_memory_retriever import InMemoryRetriever
from src.routing.scope_router import ScopeRouter
from src.service.api import create_app
from src.service.learning_pipeline import LearningCompanionPipeline


class DemoAnswerAgent:
    def answer(
        self,
        question,
        phase: LearningPhase,
        retrieved_chunks,
    ) -> AnswerDraft:
        if phase == LearningPhase.PRE_CLASS:
            answer = (
                "ก่อนเฉลย ลองอธิบายก่อนว่า loss "
                "มีความสัมพันธ์กับพารามิเตอร์อย่างไร"
            )
        elif phase == LearningPhase.DURING_CLASS:
            answer = (
                "Gradient descent ปรับพารามิเตอร์ไปในทิศทาง "
                "ตรงข้ามกับ gradient เพื่อลดค่า loss"
            )
        else:
            answer = (
                "ทบทวนว่า gradient บอกทิศทางที่ loss เพิ่มขึ้น "
                "ดังนั้นจึงปรับพารามิเตอร์ในทิศทางตรงข้าม"
            )

        return AnswerDraft(
            answer=answer,
            confidence=0.90,
            learning_signals=[],
        )


demo_chunk = MaterialChunk(
    chunk_id="chunk-demo-001",
    material_id="material-demo-001",
    material_name="gradient-descent-demo.pdf",
    page_number=4,
    chunk_index=0,
    text=(
        "Gradient descent updates model parameters "
        "in the opposite direction of the gradient "
        "to reduce the loss."
    ),
)

pipeline = LearningCompanionPipeline(
    retriever=InMemoryRetriever([demo_chunk]),
    scope_router=ScopeRouter(
        material_threshold=0.10,
        course_threshold=0.60,
    ),
    material_answer_agent=DemoAnswerAgent(),
)

app = create_app(pipeline)