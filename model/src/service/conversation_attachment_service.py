from __future__ import annotations

import json
import os
import shutil
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import RLock

from schemas.chat_attachment_contract import (
    AttachmentProcessingStatus,
    ChatAttachmentProcessResponse,
    ChatAttachmentStatusResponse,
    ChatAttachmentUploadResponse,
)
from schemas.material_contract import MaterialFileType
from src.agents.multimodal_agent import MultimodalAgent
from src.ingestion.material_storage import MaterialStorage, MaterialStorageError
from src.retrieval.conversation_knowledge_store import ConversationKnowledgeStore
from src.service.verified_kb_build_service import VerifiedKBBuildService


@dataclass
class AttachmentRecord:
    attachment_id: str
    material_id: str
    student_id: str
    conversation_id: str
    course_id: str
    class_session_id: str
    original_filename: str
    file_type: MaterialFileType
    mime_type: str
    size_bytes: int
    processing_status: AttachmentProcessingStatus
    total_pages: int = 0
    total_assets: int = 0
    total_vision_requests: int = 0
    total_vision_responses: int = 0
    verified_count: int = 0
    needs_review_count: int = 0
    rejected_count: int = 0
    error_message: str | None = None
    created_at: datetime | None = None
    expires_at: datetime | None = None
    storage_dir: str | None = None
    verified_kb_path: str | None = None


class ConversationAttachmentService:
    def __init__(
        self,
        *,
        base_dir: str | Path,
        conversation_store: ConversationKnowledgeStore,
        storage: MaterialStorage | None = None,
        build_service: VerifiedKBBuildService | None = None,
        ttl_hours: int | None = None,
    ) -> None:
        self.base_dir = Path(base_dir)
        self.conversation_store = conversation_store
        self.storage = storage or MaterialStorage(storage_root=self.base_dir / "stored")
        self.build_service = build_service or VerifiedKBBuildService()
        self.ttl_hours = ttl_hours if ttl_hours is not None else int(os.getenv("CHAT_ATTACHMENT_TTL_HOURS", "24"))
        self._lock = RLock()
        self._records: dict[str, AttachmentRecord] = {}
        self._status_dir = self.base_dir / "status"
        self._status_dir.mkdir(parents=True, exist_ok=True)

    def upload_attachment(
        self,
        *,
        student_id: str,
        conversation_id: str,
        course_id: str,
        class_session_id: str,
        filename: str,
        content_type: str,
        content: bytes,
    ) -> ChatAttachmentUploadResponse:
        self._validate_scope(student_id, conversation_id, course_id, class_session_id)
        self._validate_file(filename, content_type, content)

        attachment_id = self._make_attachment_id(student_id, conversation_id, filename, content)
        attachment_dir = self.base_dir / student_id / conversation_id / attachment_id
        attachment_dir.mkdir(parents=True, exist_ok=True)
        file_path = attachment_dir / self._safe_filename(filename)
        file_path.write_bytes(content)

        material_id = f"material-{uuid.uuid4().hex[:16]}"
        now = datetime.now(timezone.utc)
        record = AttachmentRecord(
            attachment_id=attachment_id,
            material_id=material_id,
            student_id=student_id,
            conversation_id=conversation_id,
            course_id=course_id,
            class_session_id=class_session_id,
            original_filename=Path(filename.replace("\\", "/")).name,
            file_type=self._detect_file_type(content),
            mime_type=self._normalize_mime_type(content_type),
            size_bytes=len(content),
            processing_status=AttachmentProcessingStatus.STORED,
            created_at=now,
            expires_at=now + timedelta(hours=self.ttl_hours),
            storage_dir=str(attachment_dir),
        )

        with self._lock:
            self._records[attachment_id] = record
            self._persist_status(record)

        try:
            processed = self.process_attachment(attachment_id=attachment_id)
        except Exception:
            return self._to_upload_response(record)

        return ChatAttachmentUploadResponse(
            attachment_id=processed.attachment_id,
            material_id=processed.material_id,
            student_id=processed.student_id,
            conversation_id=processed.conversation_id,
            course_id=record.course_id,
            class_session_id=record.class_session_id,
            original_filename=record.original_filename,
            file_type=record.file_type,
            mime_type=record.mime_type,
            size_bytes=record.size_bytes,
            processing_status=processed.processing_status,
        )

    def process_attachment(
        self,
        *,
        attachment_id: str,
        reviewer_id: str = "system",
        rationale: str = "Prototype semantic approval",
        kb_version: str = "chat-attachment-v1",
        agent: MultimodalAgent | None = None,
    ) -> ChatAttachmentProcessResponse:
        record = self._get_record_or_raise(attachment_id)
        record.processing_status = AttachmentProcessingStatus.PROCESSING
        self._persist_status(record)

        try:
            source_path = Path(record.storage_dir) / self._safe_filename(record.original_filename)
            if not source_path.is_file():
                raise ValueError("Attachment file is missing")
            output_dir = self.base_dir / record.student_id / record.conversation_id / record.attachment_id / "verified_kb"
            output_dir.mkdir(parents=True, exist_ok=True)
            verified_kb_path = self.build_service.build_for_material(
                material_id=record.material_id,
                material_name=record.original_filename,
                file_type=record.file_type,
                source_path=source_path,
                artifact_dir=output_dir / "artifacts",
                output_dir=output_dir,
                reviewer_id=reviewer_id,
                rationale=rationale,
                kb_version=kb_version,
                agent=agent,
            )
            record.verified_kb_path = str(verified_kb_path)
            self.conversation_store.activate_attachment(
                student_id=record.student_id,
                conversation_id=record.conversation_id,
                verified_kb_path=verified_kb_path,
            )
            record.processing_status = AttachmentProcessingStatus.READY
            record.error_message = None
            self._persist_status(record)
        except Exception as exc:
            record.processing_status = AttachmentProcessingStatus.FAILED
            record.error_message = str(exc)
            self._persist_status(record)
            raise

        return self._to_process_response(record)

    def get_status(self, attachment_id: str) -> ChatAttachmentStatusResponse:
        record = self._get_record_or_raise(attachment_id)
        return self._to_status_response(record)

    def remove_attachment(self, attachment_id: str) -> bool:
        with self._lock:
            record = self._records.get(attachment_id)
            if record is None:
                return False
            self._records.pop(attachment_id, None)
            self._delete_record_files(record)
            self.conversation_store.remove_attachment(
                student_id=record.student_id,
                conversation_id=record.conversation_id,
                material_id=record.material_id,
            )
            self._remove_status_file(attachment_id)
            return True

    def clear_conversation(self, *, student_id: str, conversation_id: str) -> int:
        self._validate_scope(student_id, conversation_id, student_id, conversation_id)
        with self._lock:
            removed = [record for record in self._records.values() if record.student_id == student_id and record.conversation_id == conversation_id]
            for record in removed:
                self._delete_record_files(record)
                self.conversation_store.remove_attachment(
                    student_id=record.student_id,
                    conversation_id=record.conversation_id,
                    material_id=record.material_id,
                )
                self._records.pop(record.attachment_id, None)
                self._remove_status_file(record.attachment_id)
            return len(removed)

    def cleanup_expired(self) -> int:
        now = datetime.now(timezone.utc)
        expired_ids = []
        with self._lock:
            for attachment_id, record in list(self._records.items()):
                if record.expires_at and record.expires_at <= now:
                    expired_ids.append(attachment_id)
            for attachment_id in expired_ids:
                record = self._records.pop(attachment_id, None)
                if record is None:
                    continue
                self._delete_record_files(record)
                self.conversation_store.remove_attachment(
                    student_id=record.student_id,
                    conversation_id=record.conversation_id,
                    material_id=record.material_id,
                )
                self._remove_status_file(attachment_id)
        return len(expired_ids)

    def _validate_scope(self, student_id: str, conversation_id: str, course_id: str, class_session_id: str) -> None:
        for value in [student_id, conversation_id, course_id, class_session_id]:
            if not str(value).strip():
                raise ValueError("student_id, conversation_id, course_id, and class_session_id must not be empty")

    def _validate_file(self, filename: str, content_type: str, content: bytes) -> None:
        if not filename.strip():
            raise ValueError("filename must not be empty")
        if not content:
            raise ValueError("Uploaded attachment must not be empty")
        if len(content) > self.storage.max_file_bytes:
            raise ValueError("Uploaded attachment exceeds maximum size")
        normalized_content_type = content_type.split(";", 1)[0].strip().lower()
        if normalized_content_type not in {"application/pdf", "image/png", "image/jpeg"}:
            raise ValueError("Unsupported attachment content type")
        try:
            self._detect_file_type(content)
        except ValueError as exc:
            raise ValueError("Uploaded attachment is not a valid PDF, PNG, or JPEG file") from exc

    def _detect_file_type(self, content: bytes) -> MaterialFileType:
        if content.startswith(b"%PDF-"):
            return MaterialFileType.PDF
        if content.startswith(b"\x89PNG\r\n\x1a\n"):
            return MaterialFileType.PNG
        if content.startswith(b"\xff\xd8\xff"):
            return MaterialFileType.JPEG
        raise ValueError("Uploaded attachment is not a valid PDF, PNG, or JPEG file")

    def _normalize_mime_type(self, content_type: str) -> str:
        return content_type.split(";", 1)[0].strip().lower()

    def _safe_filename(self, filename: str) -> str:
        original = Path(filename.replace("\\", "/")).name
        safe = "".join(ch if ch.isalnum() or ch in {"-", "_", "."} else "-" for ch in original)
        safe = safe.strip(".-") or "attachment"
        return safe

    def _make_attachment_id(self, student_id: str, conversation_id: str, filename: str, content: bytes) -> str:
        digest = uuid.uuid5(uuid.NAMESPACE_URL, f"{student_id}:{conversation_id}:{filename}:{len(content)}:{content[:32].hex()}").hex
        return f"attachment-{digest[:24]}"

    def _persist_status(self, record: AttachmentRecord) -> None:
        status_path = self._status_dir / f"{record.attachment_id}.json"
        payload = {
            "attachment_id": record.attachment_id,
            "material_id": record.material_id,
            "student_id": record.student_id,
            "conversation_id": record.conversation_id,
            "processing_status": record.processing_status.value,
            "total_pages": record.total_pages,
            "total_assets": record.total_assets,
            "total_vision_requests": record.total_vision_requests,
            "total_vision_responses": record.total_vision_responses,
            "verified_count": record.verified_count,
            "needs_review_count": record.needs_review_count,
            "rejected_count": record.rejected_count,
            "error_message": record.error_message,
            "created_at": record.created_at.isoformat() if record.created_at else None,
            "expires_at": record.expires_at.isoformat() if record.expires_at else None,
        }
        status_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _get_record_or_raise(self, attachment_id: str) -> AttachmentRecord:
        with self._lock:
            record = self._records.get(attachment_id)
            if record is None:
                raise KeyError(f"Attachment not found: {attachment_id}")
            return record

    def _delete_record_files(self, record: AttachmentRecord) -> None:
        if record.storage_dir:
            shutil.rmtree(record.storage_dir, ignore_errors=True)

    def _remove_status_file(self, attachment_id: str) -> None:
        status_path = self._status_dir / f"{attachment_id}.json"
        if status_path.exists():
            status_path.unlink()

    def _to_upload_response(self, record: AttachmentRecord) -> ChatAttachmentUploadResponse:
        return ChatAttachmentUploadResponse(
            attachment_id=record.attachment_id,
            material_id=record.material_id,
            student_id=record.student_id,
            conversation_id=record.conversation_id,
            course_id=record.course_id,
            class_session_id=record.class_session_id,
            original_filename=record.original_filename,
            file_type=record.file_type,
            mime_type=record.mime_type,
            size_bytes=record.size_bytes,
            processing_status=record.processing_status,
        )

    def _to_status_response(self, record: AttachmentRecord) -> ChatAttachmentStatusResponse:
        return ChatAttachmentStatusResponse(
            attachment_id=record.attachment_id,
            material_id=record.material_id,
            student_id=record.student_id,
            conversation_id=record.conversation_id,
            processing_status=record.processing_status,
            total_pages=record.total_pages,
            total_assets=record.total_assets,
            total_vision_requests=record.total_vision_requests,
            total_vision_responses=record.total_vision_responses,
            verified_count=record.verified_count,
            needs_review_count=record.needs_review_count,
            rejected_count=record.rejected_count,
            error_message=record.error_message,
            created_at=record.created_at or datetime.now(timezone.utc),
            expires_at=record.expires_at,
        )

    def _to_process_response(self, record: AttachmentRecord) -> ChatAttachmentProcessResponse:
        return ChatAttachmentProcessResponse(
            attachment_id=record.attachment_id,
            material_id=record.material_id,
            student_id=record.student_id,
            conversation_id=record.conversation_id,
            processing_status=record.processing_status,
            total_pages=record.total_pages,
            total_assets=record.total_assets,
            total_vision_requests=record.total_vision_requests,
            total_vision_responses=record.total_vision_responses,
            verified_count=record.verified_count,
            needs_review_count=record.needs_review_count,
            rejected_count=record.rejected_count,
            error_message=record.error_message,
            created_at=record.created_at or datetime.now(timezone.utc),
            expires_at=record.expires_at,
            verified_kb_ref=self._relative_verified_kb_ref(record),
        )

    def _relative_verified_kb_ref(self, record: AttachmentRecord) -> str | None:
        if not record.verified_kb_path:
            return None
        path = Path(record.verified_kb_path)
        if not path.is_absolute():
            return path.as_posix()
        return path.name
