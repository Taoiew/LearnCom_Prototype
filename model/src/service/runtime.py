import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from schemas.model_contract import LearningPhase
from src.agents.answer_agent import (
    AnswerDraft,
    JSONChatClient,
    RAGAnswerAgent,
)
from src.agents.llm_client import (
    LLMConfig,
    OpenAICompatibleClient,
)
from src.ingestion.pdf_ingestor import MaterialChunk
from src.retrieval.conversation_knowledge_store import (
    ConversationKnowledgeStore,
)
from src.retrieval.course_knowledge_store import (
    CourseKnowledgeStore,
)
from src.retrieval.in_memory_retriever import (
    InMemoryRetriever,
)
from src.retrieval.merged_knowledge_retriever import (
    MergedKnowledgeRetriever,
)
from src.routing.scope_router import ScopeRouter
from src.service.learning_pipeline import (
    LearningCompanionPipeline,
)


class RuntimeConfigurationError(ValueError):
    """Raised when model runtime configuration is invalid."""


@dataclass(frozen=True)
class ModelRuntimeConfig:
    mode: str

    verified_kb_path: Path | None

    local_llm_base_url: str
    local_llm_api_key: str
    local_llm_model: str
    llm_timeout_seconds: float

    top_k: int
    material_threshold: float
    course_threshold: float
    max_context_chars: int

    bootstrap_course_id: str = "course-001"
    bootstrap_class_session_id: str = "session-001"

    @classmethod
    def from_environment(
        cls,
        environment: Mapping[str, str] | None = None,
    ) -> "ModelRuntimeConfig":
        env = (
            os.environ
            if environment is None
            else environment
        )

        mode = env.get(
            "MODEL_RUNTIME_MODE",
            "demo",
        ).strip().lower()

        if mode not in {
            "demo",
            "verified_kb",
        }:
            raise RuntimeConfigurationError(
                "MODEL_RUNTIME_MODE must be "
                "'demo' or 'verified_kb'"
            )

        verified_kb_value = env.get(
            "VERIFIED_KB_PATH",
            "",
        ).strip()

        verified_kb_path = (
            Path(verified_kb_value)
            if verified_kb_value
            else None
        )

        local_llm_base_url = env.get(
            "LOCAL_LLM_BASE_URL",
            "http://127.0.0.1:8000/v1",
        ).strip()

        local_llm_api_key = env.get(
            "LOCAL_LLM_API_KEY",
            "local",
        ).strip()

        local_llm_model = env.get(
            "LOCAL_LLM_MODEL",
            "",
        ).strip()

        llm_timeout_seconds = cls._read_float(
            env=env,
            name="LLM_TIMEOUT_SECONDS",
            default=60.0,
            minimum_exclusive=0.0,
        )

        top_k = cls._read_int(
            env=env,
            name="RAG_TOP_K",
            default=3,
            minimum=1,
        )

        material_threshold = cls._read_float(
            env=env,
            name="MATERIAL_SCOPE_THRESHOLD",
            default=0.10,
            minimum=0.0,
            maximum=1.0,
        )

        course_threshold = cls._read_float(
            env=env,
            name="COURSE_SCOPE_THRESHOLD",
            default=0.60,
            minimum=0.0,
            maximum=1.0,
        )

        max_context_chars = cls._read_int(
            env=env,
            name="RAG_MAX_CONTEXT_CHARS",
            default=12000,
            minimum=1,
        )

        bootstrap_course_id = env.get(
            "BOOTSTRAP_COURSE_ID",
            "course-001",
        ).strip()

        bootstrap_class_session_id = env.get(
            "BOOTSTRAP_CLASS_SESSION_ID",
            "session-001",
        ).strip()

        if not bootstrap_course_id:
            raise RuntimeConfigurationError(
                "BOOTSTRAP_COURSE_ID must not be empty"
            )

        if not bootstrap_class_session_id:
            raise RuntimeConfigurationError(
                "BOOTSTRAP_CLASS_SESSION_ID "
                "must not be empty"
            )

        if mode == "verified_kb":
            if verified_kb_path is None:
                raise RuntimeConfigurationError(
                    "VERIFIED_KB_PATH is required when "
                    "MODEL_RUNTIME_MODE=verified_kb"
                )

            if not local_llm_base_url:
                raise RuntimeConfigurationError(
                    "LOCAL_LLM_BASE_URL is required when "
                    "MODEL_RUNTIME_MODE=verified_kb"
                )

            if not local_llm_model:
                raise RuntimeConfigurationError(
                    "LOCAL_LLM_MODEL is required when "
                    "MODEL_RUNTIME_MODE=verified_kb"
                )

        return cls(
            mode=mode,
            verified_kb_path=verified_kb_path,
            local_llm_base_url=local_llm_base_url,
            local_llm_api_key=local_llm_api_key,
            local_llm_model=local_llm_model,
            llm_timeout_seconds=llm_timeout_seconds,
            top_k=top_k,
            material_threshold=material_threshold,
            course_threshold=course_threshold,
            max_context_chars=max_context_chars,
            bootstrap_course_id=bootstrap_course_id,
            bootstrap_class_session_id=(
                bootstrap_class_session_id
            ),
        )

    @staticmethod
    def _read_int(
        env: Mapping[str, str],
        name: str,
        default: int,
        minimum: int,
    ) -> int:
        raw_value = env.get(
            name,
            str(default),
        ).strip()

        try:
            value = int(raw_value)
        except ValueError as error:
            raise RuntimeConfigurationError(
                f"{name} must be an integer"
            ) from error

        if value < minimum:
            raise RuntimeConfigurationError(
                f"{name} must be at least {minimum}"
            )

        return value

    @staticmethod
    def _read_float(
        env: Mapping[str, str],
        name: str,
        default: float,
        minimum: float | None = None,
        maximum: float | None = None,
        minimum_exclusive: float | None = None,
    ) -> float:
        raw_value = env.get(
            name,
            str(default),
        ).strip()

        try:
            value = float(raw_value)
        except ValueError as error:
            raise RuntimeConfigurationError(
                f"{name} must be a number"
            ) from error

        if (
            minimum is not None
            and value < minimum
        ):
            raise RuntimeConfigurationError(
                f"{name} must be at least {minimum}"
            )

        if (
            maximum is not None
            and value > maximum
        ):
            raise RuntimeConfigurationError(
                f"{name} must not exceed {maximum}"
            )

        if (
            minimum_exclusive is not None
            and value <= minimum_exclusive
        ):
            raise RuntimeConfigurationError(
                f"{name} must be greater than "
                f"{minimum_exclusive}"
            )

        return value


class DemoAnswerAgent:
    def answer(
        self,
        question: str,
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
                "Gradient descent ปรับพารามิเตอร์"
                "ไปในทิศทางตรงข้ามกับ gradient "
                "เพื่อลดค่า loss"
            )
        else:
            answer = (
                "ทบทวนว่า gradient บอกทิศทางที่ loss "
                "เพิ่มขึ้น ดังนั้นจึงปรับพารามิเตอร์"
                "ในทิศทางตรงข้าม"
            )

        grounded_chunk_ids = tuple(
            result.chunk.chunk_id
            for result in retrieved_chunks
        )

        return AnswerDraft(
            answer=answer,
            confidence=0.90,
            learning_signals=[],
            grounded_chunk_ids=grounded_chunk_ids,
        )


class ExtractiveAnswerAgent:
    _PDF_THAI_GLYPH_MAP = str.maketrans(
        {
            "\uf701": "ิ",
            "\uf702": "ี",
            "\uf703": "ึ",
            "\uf705": "่",
            "\uf706": "้",
            "\uf70a": "่",
            "\uf70b": "้",
            "\uf70e": "์",
            "\uf710": "ั",
            "\uf712": "็",
        }
    )
    _NOISE_PATTERNS = (
        re.compile(
            r"©\s*\d{4}.*?All rights reserved\.?",
            re.IGNORECASE,
        ),
        re.compile(
            r"©\s*\d{4}[^.]{0,120}(?:reserved\.?)?",
            re.IGNORECASE,
        ),
        re.compile(r"\bAll rights reserved\.?", re.IGNORECASE),
        re.compile(
            r"\bAmazon Web Services, Inc\.?\s+or its affiliates\.?",
            re.IGNORECASE,
        ),
    )

    def answer(
        self,
        question: str,
        phase: LearningPhase,
        retrieved_chunks,
    ) -> AnswerDraft:
        excerpts = []
        reference_pages: list[int | None] = []
        prefers_thai = self._prefers_thai(question)

        for result in retrieved_chunks[:3]:
            text = self._clean_excerpt(result.chunk.text)
            if not text:
                continue
            excerpts.append(text)
            reference_pages.append(result.chunk.page_number)

        if not excerpts:
            answer = self._empty_answer(
                prefers_thai=prefers_thai,
            )
        elif phase == LearningPhase.PRE_CLASS:
            answer = self._pre_class_answer(
                excerpts=excerpts,
                reference_pages=reference_pages,
                prefers_thai=prefers_thai,
            )
        else:
            answer = self._in_class_answer(
                excerpts=excerpts,
                reference_pages=reference_pages,
                prefers_thai=prefers_thai,
            )

        grounded_chunk_ids = tuple(
            result.chunk.chunk_id
            for result in retrieved_chunks
        )

        return AnswerDraft(
            answer=answer,
            confidence=0.80,
            learning_signals=[],
            grounded_chunk_ids=grounded_chunk_ids,
        )

    @classmethod
    def _clean_excerpt(cls, text: str) -> str:
        cleaned = cls._normalize_pdf_text(text)
        cleaned = " ".join(cleaned.strip().split())
        for pattern in cls._NOISE_PATTERNS:
            cleaned = pattern.sub("", cleaned)

        cleaned = cleaned.replace("•", " - ")
        cleaned = re.sub(r"\s*-\s*", " - ", cleaned)
        cleaned = re.sub(r"\s{2,}", " ", cleaned).strip(" -")

        if not cleaned:
            return ""

        sentences = re.split(r"(?<=[.!?])\s+", cleaned)
        useful_sentences: list[str] = []
        for sentence in sentences:
            sentence = sentence.strip(" -")
            if not sentence:
                continue
            lower = sentence.lower()
            if (
                "rights reserved" in lower
                or "amazon web services, inc" in lower
            ):
                continue
            useful_sentences.append(sentence)
            if len(useful_sentences) >= 2:
                break

        if useful_sentences:
            cleaned = " ".join(useful_sentences)

        if len(cleaned) > 260:
            cleaned = cleaned[:257].rstrip(" ,;:-") + "..."

        return cleaned

    @classmethod
    def _normalize_pdf_text(cls, text: str) -> str:
        return text.translate(cls._PDF_THAI_GLYPH_MAP)

    @staticmethod
    def _prefers_thai(question: str) -> bool:
        return bool(re.search(r"[\u0e00-\u0e7f]", question))

    @classmethod
    def _empty_answer(cls, *, prefers_thai: bool) -> str:
        if prefers_thai:
            return (
                "พบไฟล์ประกอบการเรียนแล้ว แต่ยังไม่มีข้อความที่อ่านได้"
                "มากพอสำหรับตอบคำถามนี้"
            )

        return (
            "I found the material entry, but it does "
            "not contain enough readable text to answer."
        )

    @classmethod
    def _pre_class_answer(
        cls,
        *,
        excerpts: list[str],
        reference_pages: list[int | None],
        prefers_thai: bool,
    ) -> str:
        if prefers_thai:
            return (
                "จากเอกสารที่อัปโหลด เซสชันนี้เกี่ยวกับ:\n"
                "- "
                + "\n- ".join(excerpts)
                + "\n\nก่อนเข้าเรียน ลองสรุปใจความหลักด้วยคำของตัวเอง "
                "แล้วถามต่อในจุดที่ยังไม่ชัดเจนได้เลย"
                + cls._format_references(
                    reference_pages,
                    prefers_thai=prefers_thai,
                )
            )

        return (
            "From the uploaded material, this session is "
            "about:\n- "
            + "\n- ".join(excerpts)
            + "\n\nBefore class, try explaining the key idea "
            "in your own words, then ask me about any part "
            "that feels unclear."
            + cls._format_references(
                reference_pages,
                prefers_thai=prefers_thai,
            )
        )

    @classmethod
    def _in_class_answer(
        cls,
        *,
        excerpts: list[str],
        reference_pages: list[int | None],
        prefers_thai: bool,
    ) -> str:
        if prefers_thai:
            return (
                "อ้างอิงจากเอกสารที่อัปโหลด:\n- "
                + "\n- ".join(excerpts)
                + cls._format_references(
                    reference_pages,
                    prefers_thai=prefers_thai,
                )
            )

        return (
            "Based on the uploaded material:\n- "
            + "\n- ".join(excerpts)
            + cls._format_references(
                reference_pages,
                prefers_thai=prefers_thai,
            )
        )

    @staticmethod
    def _format_references(
        pages: list[int | None],
        *,
        prefers_thai: bool,
    ) -> str:
        ordered_pages: list[int] = []
        seen_pages: set[int] = set()

        for page in pages:
            if page is None or page in seen_pages:
                continue
            seen_pages.add(page)
            ordered_pages.append(page)

        if not ordered_pages:
            return ""

        refs = ", ".join(str(page) for page in ordered_pages)
        if prefers_thai:
            return f"\n\nอ้างอิง: หน้า {refs}"

        return f"\n\nReferences: pages {refs}."


def build_pipeline(
    config: ModelRuntimeConfig,
    llm_client: JSONChatClient | None = None,
    course_store: CourseKnowledgeStore | None = None,
    conversation_store: (
        ConversationKnowledgeStore | None
    ) = None,
) -> LearningCompanionPipeline:
    scope_router = ScopeRouter(
        material_threshold=config.material_threshold,
        course_threshold=config.course_threshold,
    )

    if (
        config.mode == "demo"
        and (
            course_store is not None
            or conversation_store is not None
        )
    ):
        resolved_course_store = (
            course_store
            if course_store is not None
            else CourseKnowledgeStore()
        )

        resolved_conversation_store = (
            conversation_store
            if conversation_store is not None
            else ConversationKnowledgeStore()
        )

        return LearningCompanionPipeline(
            retriever=MergedKnowledgeRetriever(
                course_store=resolved_course_store,
                conversation_store=(
                    resolved_conversation_store
                ),
            ),
            scope_router=scope_router,
            material_answer_agent=ExtractiveAnswerAgent(),
            top_k=config.top_k,
        )

    if config.mode == "demo":
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

        return LearningCompanionPipeline(
            retriever=InMemoryRetriever(
                [demo_chunk]
            ),
            scope_router=scope_router,
            material_answer_agent=DemoAnswerAgent(),
            top_k=config.top_k,
        )

    if config.verified_kb_path is None:
        raise RuntimeConfigurationError(
            "verified_kb_path is required"
        )

    resolved_course_store = (
        course_store
        if course_store is not None
        else CourseKnowledgeStore()
    )

    resolved_conversation_store = (
        conversation_store
        if conversation_store is not None
        else ConversationKnowledgeStore()
    )

    resolved_course_store.activate(
        course_id=config.bootstrap_course_id,
        class_session_id=(
            config.bootstrap_class_session_id
        ),
        verified_kb_path=config.verified_kb_path,
    )

    retriever = MergedKnowledgeRetriever(
        course_store=resolved_course_store,
        conversation_store=(
            resolved_conversation_store
        ),
    )

    resolved_client = llm_client

    if resolved_client is None:
        resolved_client = OpenAICompatibleClient(
            LLMConfig(
                base_url=config.local_llm_base_url,
                model=config.local_llm_model,
                api_key=config.local_llm_api_key,
                timeout_seconds=(
                    config.llm_timeout_seconds
                ),
            )
        )

    answer_agent = RAGAnswerAgent(
        llm_client=resolved_client,
        max_context_chars=(
            config.max_context_chars
        ),
    )

    return LearningCompanionPipeline(
        retriever=retriever,
        scope_router=scope_router,
        material_answer_agent=answer_agent,
        top_k=config.top_k,
    )


def build_pipeline_from_environment(
    environment: Mapping[str, str] | None = None,
    llm_client: JSONChatClient | None = None,
    course_store: CourseKnowledgeStore | None = None,
    conversation_store: (
        ConversationKnowledgeStore | None
    ) = None,
) -> LearningCompanionPipeline:
    config = ModelRuntimeConfig.from_environment(
        environment
    )

    return build_pipeline(
        config=config,
        llm_client=llm_client,
        course_store=course_store,
        conversation_store=conversation_store,
    )
