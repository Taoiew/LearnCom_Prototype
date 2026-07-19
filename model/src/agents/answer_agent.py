import json
from dataclasses import dataclass

from schemas.model_contract import LearningPhase, LearningSignal
from src.agents.llm_client import OpenAICompatibleClient
from src.retrieval.in_memory_retriever import RetrievedChunk


@dataclass(frozen=True)
class AnswerDraft:
    answer: str
    confidence: float
    learning_signals: list[LearningSignal]


class RAGAnswerAgent:
    BASE_PROMPT = """
You are a personal teaching assistant.
You are not the instructor and must never claim to be the instructor.

Use only the supplied material context.
Return JSON with this structure:

{
  "answer": "string",
  "confidence": 0.0,
  "learning_signals": [
    {
      "topic": "string",
      "signal_type": "string",
      "severity": 0.0,
      "explanation": "string"
    }
  ]
}

Do not include Markdown outside the JSON.
""".strip()

    PHASE_INSTRUCTIONS = {
        LearningPhase.PRE_CLASS: (
            "PRE-CLASS: Assess readiness using questions and hints. "
            "Do not reveal the complete answer immediately."
        ),
        LearningPhase.DURING_CLASS: (
            "DURING-CLASS: Teach clearly and provide a complete "
            "explanation grounded in the material."
        ),
        LearningPhase.AFTER_CLASS: (
            "AFTER-CLASS: Explain completely, identify what the "
            "student may have missed, and support revision."
        ),
    }

    def __init__(
        self,
        llm_client: OpenAICompatibleClient,
    ) -> None:
        self.llm_client = llm_client

    def answer(
        self,
        question: str,
        phase: LearningPhase,
        retrieved_chunks: list[RetrievedChunk],
    ) -> AnswerDraft:
        contexts = [
            {
                "material_id": result.chunk.material_id,
                "material_name": result.chunk.material_name,
                "chunk_id": result.chunk.chunk_id,
                "page_number": result.chunk.page_number,
                "text": result.chunk.text,
                "retrieval_score": result.score,
            }
            for result in retrieved_chunks
        ]

        system_prompt = (
            f"{self.BASE_PROMPT}\n\n"
            f"{self.PHASE_INSTRUCTIONS[phase]}"
        )

        user_prompt = json.dumps(
            {
                "question": question,
                "phase": phase.value,
                "material_context": contexts,
            },
            ensure_ascii=False,
        )

        result = self.llm_client.chat_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.0,
        )

        signals = [
            LearningSignal(**signal)
            for signal in result.get("learning_signals", [])
        ]

        return AnswerDraft(
            answer=result["answer"],
            confidence=result["confidence"],
            learning_signals=signals,
        )