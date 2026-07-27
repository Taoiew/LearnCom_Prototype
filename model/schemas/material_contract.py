from enum import Enum

from pydantic import BaseModel, Field


class MaterialFileType(str, Enum):
    PDF = "pdf"
    PNG = "png"
    JPEG = "jpeg"


class MaterialUploadStatus(str, Enum):
    STORED = "stored"


class MaterialStoredProcessingStatus(str, Enum):
    STORED = "stored"
    PROCESSING = "processing"
    PROCESSED = "processed"
    NEEDS_REVIEW = "needs_review"
    REJECTED = "rejected"
    FAILED = "failed"


class MaterialUploadResponse(BaseModel):
    material_id: str
    original_filename: str
    stored_filename: str
    stored_path: str

    file_type: MaterialFileType
    mime_type: str
    size_bytes: int = Field(gt=0)
    sha256: str = Field(
        min_length=64,
        max_length=64,
    )

    status: MaterialUploadStatus = (
        MaterialUploadStatus.STORED
    )


class MaterialStatusResponse(BaseModel):
    material_id: str
    file_type: MaterialFileType
    processing_status: MaterialStoredProcessingStatus

    original_filename: str
    stored_path: str

    total_pages: int = Field(ge=0)
    total_assets: int = Field(ge=0)
    total_vision_requests: int = Field(ge=0)
    total_vision_responses: int = Field(ge=0)
    verified_count: int = Field(ge=0)
    needs_review_count: int = Field(ge=0)
    rejected_count: int = Field(ge=0)

    error_message: str | None = None
