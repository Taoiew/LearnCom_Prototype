from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from schemas.material_contract import MaterialFileType


class AttachmentProcessingStatus(str, Enum):
    STORED = "stored"
    PROCESSING = "processing"
    READY = "ready"
    NEEDS_REVIEW = "needs_review"
    FAILED = "failed"


class ChatAttachmentUploadResponse(BaseModel):
    attachment_id: str
    material_id: str
    student_id: str
    conversation_id: str
    course_id: str
    class_session_id: str
    original_filename: str
    file_type: MaterialFileType
    mime_type: str
    size_bytes: int = Field(gt=0)
    processing_status: AttachmentProcessingStatus


class ChatAttachmentStatusResponse(BaseModel):
    attachment_id: str
    material_id: str
    student_id: str
    conversation_id: str
    processing_status: AttachmentProcessingStatus
    total_pages: int = Field(ge=0)
    total_assets: int = Field(ge=0)
    total_vision_requests: int = Field(ge=0)
    total_vision_responses: int = Field(ge=0)
    verified_count: int = Field(ge=0)
    needs_review_count: int = Field(ge=0)
    rejected_count: int = Field(ge=0)
    error_message: str | None = None
    created_at: datetime
    expires_at: datetime | None = None


class ChatAttachmentProcessResponse(BaseModel):
    attachment_id: str
    material_id: str
    student_id: str
    conversation_id: str
    processing_status: AttachmentProcessingStatus
    total_pages: int = Field(ge=0)
    total_assets: int = Field(ge=0)
    total_vision_requests: int = Field(ge=0)
    total_vision_responses: int = Field(ge=0)
    verified_count: int = Field(ge=0)
    needs_review_count: int = Field(ge=0)
    rejected_count: int = Field(ge=0)
    error_message: str | None = None
    created_at: datetime
    expires_at: datetime | None = None
    verified_kb_ref: str | None = None


class ChatAttachmentWithResponse(BaseModel):
    attachment: ChatAttachmentUploadResponse
    chat: dict
