from enum import Enum

from pydantic import BaseModel, Field


class ReviewStatus(str, Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"
    NEEDS_REVIEW = "needs_review"


class EnrichedKnowledge(BaseModel):
    knowledge_id: str
    material_id: str
    source_chunk_ids: list[str] = Field(min_length=1)
    page_numbers: list[int] = Field(min_length=1)

    topic: str
    summary: str
    key_concepts: list[str] = Field(default_factory=list)
    learning_objectives: list[str] = Field(default_factory=list)
    common_misconceptions: list[str] = Field(default_factory=list)
    suggested_questions: list[str] = Field(default_factory=list)

    source_quote: str
    rubric_ids: list[str] = Field(default_factory=list)

    confidence: float = Field(ge=0, le=1)
    review_status: ReviewStatus = ReviewStatus.PENDING
    agent_model: str
    prompt_version: str = "v1"