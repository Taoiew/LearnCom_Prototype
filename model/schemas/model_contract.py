from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class LearningPhase(str, Enum):
    PRE_CLASS = "pre_class"
    DURING_CLASS = "during_class"
    AFTER_CLASS = "after_class"


class ScopeDecision(str, Enum):
    IN_MATERIAL = "in_material"
    COURSE_RELATED_OUTSIDE_MATERIAL = "course_related_outside_material"
    UNRELATED = "unrelated"
    UNSAFE = "unsafe"


class Citation(BaseModel):
    material_id: str
    material_name: str

    chunk_id: str
    knowledge_id: Optional[str] = None

    source_chunk_ids: List[str] = Field(
        default_factory=list
    )
    asset_ids: List[str] = Field(
        default_factory=list
    )

    page_number: Optional[int] = None
    quote: Optional[str] = None

    relevance_score: float = Field(ge=0, le=1)


class ChatRequest(BaseModel):
    student_id: str
    course_id: str
    class_session_id: str
    phase: LearningPhase
    question: str = Field(min_length=1)
    conversation_id: Optional[str] = None


class LearningSignal(BaseModel):
    topic: str
    signal_type: str
    severity: float = Field(ge=0, le=1)
    material_id: Optional[str] = None
    chunk_id: Optional[str] = None
    explanation: Optional[str] = None


class ChatResponse(BaseModel):
    answer: str
    scope: ScopeDecision
    citations: List[Citation] = Field(default_factory=list)
    learning_signals: List[LearningSignal] = Field(default_factory=list)
    used_external_agent: bool = False
    confidence: float = Field(ge=0, le=1)