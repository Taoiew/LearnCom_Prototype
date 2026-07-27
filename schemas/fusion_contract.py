from datetime import datetime
from enum import Enum

from pydantic import (
    AwareDatetime,
    BaseModel,
    Field,
    model_validator,
)

from schemas.kb_contract import ReviewStatus


class SemanticDecision(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"


class ApprovalSource(str, Enum):
    HUMAN = "human"
    INDEPENDENT_JUDGE = "independent_judge"


class SemanticApproval(BaseModel):
    request_id: str = Field(min_length=1)
    decision: SemanticDecision
    source: ApprovalSource

    reviewer_id: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    reviewed_at: AwareDatetime


class FusedKnowledge(BaseModel):
    knowledge_id: str = Field(min_length=1)

    material_id: str = Field(min_length=1)
    material_name: str = Field(min_length=1)
    page_number: int = Field(ge=1)

    source_request_id: str = Field(min_length=1)
    source_chunk_ids: list[str] = Field(
        default_factory=list
    )
    asset_ids: list[str] = Field(min_length=1)

    element_ids: list[str] = Field(
        default_factory=list
    )
    table_ids: list[str] = Field(
        default_factory=list
    )

    text_content: str = ""
    visual_content: str = ""
    content: str = Field(min_length=1)

    confidence: float = Field(ge=0, le=1)
    review_status: ReviewStatus

    agent_model: str = Field(min_length=1)
    prompt_version: str = Field(min_length=1)
    fusion_version: str = "fusion-v1"

    semantic_approval: SemanticApproval
    created_at: AwareDatetime

    @model_validator(mode="after")
    def validate_verified_knowledge(
        self,
    ) -> "FusedKnowledge":
        if self.review_status is not ReviewStatus.VERIFIED:
            raise ValueError(
                "FusedKnowledge must have verified status"
            )

        if (
            self.semantic_approval.decision
            is not SemanticDecision.APPROVED
        ):
            raise ValueError(
                "FusedKnowledge requires semantic approval"
            )

        if (
            self.semantic_approval.request_id
            != self.source_request_id
        ):
            raise ValueError(
                "semantic approval request_id does not "
                "match source_request_id"
            )

        return self