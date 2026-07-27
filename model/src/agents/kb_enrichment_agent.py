import hashlib
import json
from abc import ABC, abstractmethod

from schemas.kb_contract import EnrichedKnowledge
from src.agents.llm_client import OpenAICompatibleClient
from src.ingestion.pdf_ingestor import MaterialChunk


class KBEnrichmentAgent(ABC):
    @abstractmethod
    def enrich(self, chunk: MaterialChunk) -> EnrichedKnowledge:
        """Convert a source KB chunk into an enriched KB record."""


class MockKBEnrichmentAgent(KBEnrichmentAgent):
    def enrich(self, chunk: MaterialChunk) -> EnrichedKnowledge:
        topic = self._extract_topic(chunk.text)

        return EnrichedKnowledge(
            knowledge_id=self._create_knowledge_id(chunk.chunk_id),
            material_id=chunk.material_id,
            source_chunk_ids=[chunk.chunk_id],
            page_numbers=[chunk.page_number],
            topic=topic,
            summary=chunk.text,
            key_concepts=[],
            learning_objectives=[
                f"Explain the key concept related to {topic}"
            ],
            common_misconceptions=[],
            suggested_questions=[
                f"What are the important principles of {topic}?"
            ],
            source_quote=chunk.text[:300],
            confidence=0.50,
            agent_model="mock-agent",
            prompt_version="v1",
        )

    @staticmethod
    def _extract_topic(text: str) -> str:
        first_sentence = text.split(".")[0].strip()
        return first_sentence[:100] or "Untitled topic"

    @staticmethod
    def _create_knowledge_id(chunk_id: str) -> str:
        digest = hashlib.sha256(chunk_id.encode("utf-8")).hexdigest()[:16]
        return f"kb-{digest}"


class LLMKBEnrichmentAgent(KBEnrichmentAgent):
    SYSTEM_PROMPT = """
You are a knowledge-base enrichment agent for an educational system.

Use only the supplied source material.
Do not add facts that are unsupported by the source.
Return one JSON object with these fields:

{
  "topic": "string",
  "summary": "string",
  "key_concepts": ["string"],
  "learning_objectives": ["string"],
  "common_misconceptions": ["string"],
  "suggested_questions": ["string"],
  "source_quote": "exact quote copied from source",
  "confidence": 0.0
}

The source_quote must be copied exactly from the source material.
confidence must be between 0 and 1.
Do not include Markdown.
""".strip()

    def __init__(
        self,
        llm_client: OpenAICompatibleClient,
        agent_model: str,
        prompt_version: str = "v1",
    ) -> None:
        self.llm_client = llm_client
        self.agent_model = agent_model
        self.prompt_version = prompt_version

    def enrich(self, chunk: MaterialChunk) -> EnrichedKnowledge:
        user_prompt = json.dumps(
            {
                "material_id": chunk.material_id,
                "chunk_id": chunk.chunk_id,
                "page_number": chunk.page_number,
                "source_text": chunk.text,
            },
            ensure_ascii=False,
        )

        result = self.llm_client.chat_json(
            system_prompt=self.SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.0,
        )

        return EnrichedKnowledge(
            knowledge_id=self._create_knowledge_id(chunk.chunk_id),
            material_id=chunk.material_id,
            source_chunk_ids=[chunk.chunk_id],
            page_numbers=[chunk.page_number],
            topic=result["topic"],
            summary=result["summary"],
            key_concepts=result.get("key_concepts", []),
            learning_objectives=result.get(
                "learning_objectives",
                [],
            ),
            common_misconceptions=result.get(
                "common_misconceptions",
                [],
            ),
            suggested_questions=result.get(
                "suggested_questions",
                [],
            ),
            source_quote=result["source_quote"],
            confidence=result["confidence"],
            agent_model=self.agent_model,
            prompt_version=self.prompt_version,
        )

    @staticmethod
    def _create_knowledge_id(chunk_id: str) -> str:
        digest = hashlib.sha256(chunk_id.encode("utf-8")).hexdigest()[:16]
        return f"kb-{digest}"
