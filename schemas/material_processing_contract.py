from enum import Enum

from pydantic import BaseModel, Field

from schemas.material_contract import MaterialFileType


class MaterialProcessingStatus(str, Enum):
    PROCESSING = "processing"
    COMPLETED = "completed"
    NEEDS_REVIEW = "needs_review"
    REJECTED = "rejected"
    FAILED = "failed"


class MaterialProcessingResponse(BaseModel):
    material_id: str
    file_type: MaterialFileType
    status: MaterialProcessingStatus

    total_pages: int = Field(ge=0)
    total_vision_requests: int = Field(ge=0)
    total_vision_responses: int = Field(ge=0)
    verified_count: int = Field(ge=0)
    needs_review_count: int = Field(ge=0)
    rejected_count: int = Field(ge=0)

    pages_manifest_path: str
    assets_manifest_path: str
    vision_requests_path: str
    vision_responses_path: str | None = None
    vision_verifications_path: str | None = None

    error: str | None = None


class MaterialProcessAPIResponse(BaseModel):
    material_id: str
    file_type: MaterialFileType
    processing_status: MaterialProcessingStatus

    total_pages: int = Field(ge=0)
    total_assets: int = Field(ge=0)
    total_vision_requests: int = Field(ge=0)
    total_vision_responses: int = Field(ge=0)
    verified_count: int = Field(ge=0)
    needs_review_count: int = Field(ge=0)
    rejected_count: int = Field(ge=0)

    pages_manifest_ref: str
    assets_manifest_ref: str
    vision_requests_ref: str
    vision_responses_ref: str | None = None
    vision_verifications_ref: str | None = None

    error: str | None = None
