import json
import os
import uuid
from collections.abc import Callable
from contextlib import AbstractContextManager, nullcontext
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import (
    FastAPI,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from pydantic import BaseModel, Field

from schemas.chat_attachment_contract import (
    AttachmentProcessingStatus,
    ChatAttachmentProcessResponse,
    ChatAttachmentStatusResponse,
    ChatAttachmentUploadResponse,
)
from schemas.material_contract import (
    MaterialStatusResponse,
    MaterialUploadResponse,
)
from schemas.material_processing_contract import (
    MaterialProcessAPIResponse,
    MaterialProcessingResponse,
)
from schemas.model_contract import ChatRequest, ChatResponse
from src.agents.multimodal_agent import MultimodalAgent
from src.agents.multimodal_client import MultimodalClientError
from src.agents.multimodal_factory import (
    multimodal_agent_context,
)
from src.ingestion.material_storage import (
    MaterialStorage,
    MaterialStorageError,
)
from src.service.conversation_attachment_service import (
    ConversationAttachmentService,
)
from src.service.material_processing_service import (
    MaterialProcessingError,
    MaterialProcessingProviderError,
    MaterialProcessingService,
)
from src.service.verified_kb_build_service import VerifiedKBBuildService
from src.retrieval.course_knowledge_store import CourseKnowledgeStore


class ChatAPIRequest(BaseModel):
    request: ChatRequest
    course_relevance_score: float = Field(ge=0, le=1)
    unsafe: bool = False


class MaterialActivateRequest(BaseModel):
    course_id: str = Field(min_length=1)
    class_session_id: str = Field(min_length=1)


class MaterialActivateResponse(BaseModel):
    material_id: str
    course_id: str
    class_session_id: str
    verified_kb_ref: str
    active_material_ids: list[str]


class RubricCreateRequest(BaseModel):
    course_id: str = Field(min_length=1)
    class_session_id: str = Field(min_length=1)
    rubric_name: str = Field(default="rubric")
    criteria: list[str] = Field(default_factory=list)


class RubricUploadRequest(BaseModel):
    course_id: str = Field(min_length=1)
    class_session_id: str = Field(min_length=1)
    rubric_name: str = Field(default="rubric")
    criteria: list[str] = Field(default_factory=list)


class RubricResponse(BaseModel):
    rubric_id: str
    course_id: str
    class_session_id: str
    rubric_name: str
    criteria: list[str] = Field(default_factory=list)


class RubricEvaluationRequest(BaseModel):
    score: float = Field(ge=0, le=1)
    notes: str | None = None


class RubricEvaluationResponse(BaseModel):
    rubric_id: str
    score: float
    notes: str | None = None
    status: str = "evaluated"


class SessionReportCreateRequest(BaseModel):
    title: str = Field(default="session-report")
    summary: str = Field(default="")


class SessionReportResponse(BaseModel):
    report_id: str
    course_id: str
    class_session_id: str
    title: str
    summary: str
    generated_at: str


class InMemoryRubricService:
    def __init__(self) -> None:
        self._rubrics: dict[str, dict[str, Any]] = {}

    def create(
        self,
        *,
        course_id: str,
        class_session_id: str,
        rubric_name: str,
        criteria: list[str],
    ) -> RubricResponse:
        rubric_id = f"rubric-{uuid.uuid4().hex[:8]}"
        payload = {
            "rubric_id": rubric_id,
            "course_id": course_id,
            "class_session_id": class_session_id,
            "rubric_name": rubric_name,
            "criteria": list(criteria),
        }
        self._rubrics[rubric_id] = payload
        return RubricResponse(**payload)

    def list(self, *, course_id: str, class_session_id: str) -> list[RubricResponse]:
        return [
            RubricResponse(**payload)
            for payload in self._rubrics.values()
            if payload["course_id"] == course_id and payload["class_session_id"] == class_session_id
        ]

    def evaluate(self, *, rubric_id: str, score: float, notes: str | None) -> RubricEvaluationResponse:
        payload = self._rubrics.get(rubric_id)
        if payload is None:
            raise KeyError(f"Rubric not found: {rubric_id}")
        return RubricEvaluationResponse(rubric_id=rubric_id, score=score, notes=notes)


class InMemorySessionReportService:
    def __init__(self) -> None:
        self._reports: dict[str, dict[str, Any]] = {}

    def generate(
        self,
        *,
        course_id: str,
        class_session_id: str,
        title: str,
        summary: str,
    ) -> SessionReportResponse:
        report_id = f"report-{uuid.uuid4().hex[:8]}"
        payload = {
            "report_id": report_id,
            "course_id": course_id,
            "class_session_id": class_session_id,
            "title": title,
            "summary": summary,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        self._reports[report_id] = payload
        return SessionReportResponse(**payload)

    def list(self, *, course_id: str, class_session_id: str) -> list[SessionReportResponse]:
        return [
            SessionReportResponse(**payload)
            for payload in self._reports.values()
            if payload["course_id"] == course_id and payload["class_session_id"] == class_session_id
        ]


def create_app(
    pipeline: Any,
    material_storage: MaterialStorage | None = None,
    conversation_attachment_service: (
        ConversationAttachmentService | None
    ) = None,
    material_processing_service: (
        MaterialProcessingService | None
    ) = None,
    material_processing_service_factory: (
        Callable[
            [MaterialStorage],
            MaterialProcessingService,
        ]
        | None
    ) = None,
    multimodal_agent_context_factory: (
        Callable[
            [str],
            AbstractContextManager[
                MultimodalAgent | None
            ],
        ]
        | None
    ) = None,
    rubric_service: InMemoryRubricService | None = None,
    session_report_service: InMemorySessionReportService | None = None,
    course_store: CourseKnowledgeStore | None = None,
) -> FastAPI:
    app = FastAPI(
        title="Learning Companion Model API",
        version="0.1.0",
    )

    storage = (
        material_storage
        if material_storage is not None
        else MaterialStorage(
            storage_root=Path(
                os.getenv(
                    "MATERIAL_UPLOAD_DIR",
                    "data/uploads",
                )
            )
        )
    )

    if material_processing_service is not None:
        processing_service = material_processing_service
    elif material_processing_service_factory is not None:
        processing_service = (
            material_processing_service_factory(storage)
        )
    else:
        processing_service = MaterialProcessingService(
            storage=storage,
            work_root=Path(
                os.getenv(
                    "MATERIAL_PROCESSING_WORK_DIR",
                    "data/material_processing",
                )
            ),
        )

    agent_context_factory = (
        multimodal_agent_context_factory
        or multimodal_agent_context
    )

    attachment_service = (
        conversation_attachment_service
    )
    rubric_service_impl = rubric_service or InMemoryRubricService()
    session_report_service_impl = session_report_service or InMemorySessionReportService()
    course_store_impl = course_store
    verified_kb_builder = VerifiedKBBuildService()

    @app.get("/health")
    def health() -> dict[str, str]:
        return {
            "status": "ok",
            "service": "learning-companion-model",
        }

    @app.post(
        "/v1/chat",
        response_model=ChatResponse,
    )
    def chat(payload: ChatAPIRequest) -> ChatResponse:
        return pipeline.run(
            request=payload.request,
            course_relevance_score=(
                payload.course_relevance_score
            ),
            unsafe=payload.unsafe,
        )

    @app.post(
        "/v1/chat/with-attachment",
        response_model=dict,
    )
    async def chat_with_attachment(
        request_json: str = Form(""),
        course_relevance_score: float = Form(0.0),
        unsafe: bool = Form(False),
        file: UploadFile = File(...),
    ) -> dict[str, Any]:
        if attachment_service is None:
            raise HTTPException(
                status_code=(
                    status.HTTP_500_INTERNAL_SERVER_ERROR
                ),
                detail=(
                    "Conversation attachment service "
                    "is not configured"
                ),
            )

        try:
            request = ChatRequest.model_validate_json(
                request_json
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "request_json must be a valid "
                    "ChatRequest"
                ),
            ) from exc

        if not request.conversation_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "conversation_id is required "
                    "for chat attachments"
                ),
            )

        try:
            content = await file.read()
            with _chat_attachment_agent_context(
                agent_context_factory
            ) as agent:
                attachment = (
                    attachment_service.upload_attachment(
                        student_id=request.student_id,
                        conversation_id=(
                            request.conversation_id
                        ),
                        course_id=request.course_id,
                        class_session_id=(
                            request.class_session_id
                        ),
                        filename=(
                            file.filename
                            or "attachment"
                        ),
                        content_type=(
                            file.content_type
                            or "application/octet-stream"
                        ),
                        content=content,
                        agent=agent,
                        auto_process=False,
                    )
                )

                processed = (
                    attachment_service.process_attachment(
                        attachment_id=(
                            attachment.attachment_id
                        ),
                        agent=agent,
                    )
                )

            chat_response = pipeline.run(
                request=request,
                course_relevance_score=(
                    course_relevance_score
                ),
                unsafe=unsafe,
            )

            return {
                "attachment": processed.model_dump(
                    mode="json"
                ),
                "chat": chat_response.model_dump(
                    mode="json"
                ),
            }

        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc

        except KeyError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(exc),
            ) from exc

        except RuntimeError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=str(exc),
            ) from exc

        finally:
            await file.close()

    @app.post(
        "/v1/chat/attachments",
        response_model=ChatAttachmentUploadResponse,
        status_code=status.HTTP_201_CREATED,
    )
    async def upload_chat_attachment_via_json(
        student_id: str = Form(""),
        conversation_id: str = Form(""),
        course_id: str = Form(""),
        class_session_id: str = Form(""),
        file: UploadFile = File(...),
    ) -> ChatAttachmentUploadResponse:
        if attachment_service is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Conversation attachment service is not configured",
            )

        try:
            content = await file.read()
            with _chat_attachment_agent_context(
                agent_context_factory
            ) as agent:
                return attachment_service.upload_attachment(
                    student_id=student_id,
                    conversation_id=conversation_id,
                    course_id=course_id,
                    class_session_id=class_session_id,
                    filename=file.filename or "attachment",
                    content_type=(
                        file.content_type
                        or "application/octet-stream"
                    ),
                    content=content,
                    agent=agent,
                )
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc
        finally:
            await file.close()

    @app.post(
        "/v1/chat/attachments/{attachment_id}/process",
        response_model=ChatAttachmentProcessResponse,
    )
    def process_chat_attachment_route(attachment_id: str) -> ChatAttachmentProcessResponse:
        if attachment_service is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Conversation attachment service is not configured",
            )

        try:
            with _chat_attachment_agent_context(
                agent_context_factory
            ) as agent:
                return attachment_service.process_attachment(
                    attachment_id=attachment_id,
                    agent=agent,
                )
        except KeyError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    @app.get(
        "/v1/chat/attachments/{attachment_id}/status",
        response_model=ChatAttachmentStatusResponse,
    )
    def chat_attachment_status_route(attachment_id: str) -> ChatAttachmentStatusResponse:
        if attachment_service is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Conversation attachment service is not configured",
            )

        try:
            return attachment_service.get_status(attachment_id)
        except KeyError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    @app.delete(
        "/v1/chat/attachments/{attachment_id}",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    def delete_chat_attachment_route(attachment_id: str) -> None:
        if attachment_service is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Conversation attachment service is not configured",
            )

        if not attachment_service.remove_attachment(attachment_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Attachment not found: {attachment_id}")

    @app.delete(
        "/v1/chat/conversations/{student_id}/{conversation_id}/attachments",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    def clear_chat_conversation_attachments_route(student_id: str, conversation_id: str) -> None:
        if attachment_service is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Conversation attachment service is not configured",
            )

        attachment_service.clear_conversation(student_id=student_id, conversation_id=conversation_id)

    @app.post("/v1/rubrics", response_model=RubricResponse)
    def create_rubric(payload: RubricCreateRequest) -> RubricResponse:
        return rubric_service_impl.create(
            course_id=payload.course_id,
            class_session_id=payload.class_session_id,
            rubric_name=payload.rubric_name,
            criteria=payload.criteria,
        )

    @app.post("/v1/rubrics/upload", response_model=RubricResponse)
    def upload_rubric(payload: RubricUploadRequest) -> RubricResponse:
        return rubric_service_impl.create(
            course_id=payload.course_id,
            class_session_id=payload.class_session_id,
            rubric_name=payload.rubric_name,
            criteria=payload.criteria,
        )

    @app.get("/v1/rubrics/{course_id}/{class_session_id}", response_model=list[RubricResponse])
    def get_rubrics(course_id: str, class_session_id: str) -> list[RubricResponse]:
        return rubric_service_impl.list(course_id=course_id, class_session_id=class_session_id)

    @app.post("/v1/rubrics/{rubric_id}/evaluate", response_model=RubricEvaluationResponse)
    def evaluate_rubric(rubric_id: str, payload: RubricEvaluationRequest) -> RubricEvaluationResponse:
        return rubric_service_impl.evaluate(rubric_id=rubric_id, score=payload.score, notes=payload.notes)

    @app.post(
        "/v1/session-reports/{course_id}/{class_session_id}/generate",
        response_model=SessionReportResponse,
    )
    def generate_session_report(course_id: str, class_session_id: str, payload: SessionReportCreateRequest) -> SessionReportResponse:
        return session_report_service_impl.generate(
            course_id=course_id,
            class_session_id=class_session_id,
            title=payload.title,
            summary=payload.summary,
        )

    @app.get("/v1/session-reports/{course_id}/{class_session_id}", response_model=list[SessionReportResponse])
    def list_session_reports(course_id: str, class_session_id: str) -> list[SessionReportResponse]:
        return session_report_service_impl.list(course_id=course_id, class_session_id=class_session_id)

    @app.post(
        "/v1/materials/upload",
        response_model=MaterialUploadResponse,
        status_code=status.HTTP_201_CREATED,
    )
    async def upload_material(
        file: UploadFile = File(...),
    ) -> MaterialUploadResponse:
        try:
            content = await file.read(
                storage.max_file_bytes + 1
            )

            return storage.store(
                filename=file.filename or "",
                content_type=file.content_type or "",
                content=content,
            )

        except MaterialStorageError as exc:
            message = str(exc)

            if "exceeds maximum size" in message:
                status_code = (
                    status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
                )
            elif "Unsupported material content type" in message:
                status_code = (
                    status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
                )
            else:
                status_code = status.HTTP_400_BAD_REQUEST

            raise HTTPException(
                status_code=status_code,
                detail=message,
            ) from exc

        finally:
            await file.close()

    @app.post(
        "/v1/materials/{material_id}/process",
        response_model=MaterialProcessAPIResponse,
    )
    def process_material(
        material_id: str,
    ) -> MaterialProcessAPIResponse:
        mode = _material_multimodal_mode()

        try:
            processing_service.mark_processing(material_id)

            with agent_context_factory(mode) as agent:
                processing_response = (
                    processing_service.process(
                        material_id=material_id,
                        agent=agent,
                    )
                )
        except ValueError as exc:
            _persist_processing_failure_safely(
                processing_service=processing_service,
                material_id=material_id,
                error_message=str(exc),
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc
        except MaterialProcessingProviderError as exc:
            message = str(exc)
            _persist_processing_failure_safely(
                processing_service=processing_service,
                material_id=material_id,
                error_message=message,
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=message,
            ) from exc
        except MultimodalClientError as exc:
            message = _external_provider_failure_message(exc)
            _persist_processing_failure_safely(
                processing_service=processing_service,
                material_id=material_id,
                error_message=message,
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=message,
            ) from exc
        except MaterialProcessingError as exc:
            message = str(exc)
            status_code = _material_processing_error_status(
                message
            )
            if status_code != status.HTTP_404_NOT_FOUND:
                _persist_processing_failure_safely(
                    processing_service=processing_service,
                    material_id=material_id,
                    error_message=message,
                )

            raise HTTPException(
                status_code=status_code,
                detail=message,
            ) from exc

        if processing_response.status.value == "failed":
            status_code = (
                status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
                if _is_unsupported_media_error(
                    processing_response.error
                )
                else status.HTTP_400_BAD_REQUEST
            )
            processing_service.persist_result(
                processing_response
            )
            raise HTTPException(
                status_code=status_code,
                detail=(
                    processing_response.error
                    or "Material processing failed"
                ),
            )

        processing_service.persist_result(
            processing_response
        )

        return _to_material_process_api_response(
            processing_response=processing_response,
            work_root=processing_service.work_root,
        )

    @app.get(
        "/v1/materials/{material_id}/status",
        response_model=MaterialStatusResponse,
    )
    def material_status(
        material_id: str,
    ) -> MaterialStatusResponse:
        try:
            return processing_service.get_status(material_id)
        except MaterialProcessingError as exc:
            message = str(exc)
            raise HTTPException(
                status_code=_material_status_error_status(
                    message
                ),
                detail=message,
            ) from exc

    @app.post(
        "/v1/materials/{material_id}/activate",
        response_model=MaterialActivateResponse,
    )
    def activate_material(
        material_id: str,
        payload: MaterialActivateRequest,
    ) -> MaterialActivateResponse:
        if course_store_impl is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Course knowledge store is not configured",
            )

        try:
            material = storage.get(material_id)
            material_status_response = (
                processing_service.get_status(material_id)
            )

            if material_status_response.processing_status == "failed":
                raise ValueError(
                    "Material processing failed and cannot be activated"
                )

            artifact_dir = (
                processing_service.work_root / material_id
            )
            output_dir = artifact_dir / "verified_kb"
            output_dir.mkdir(parents=True, exist_ok=True)

            try:
                verified_kb_path = (
                    verified_kb_builder._build_verified_kb_from_artifacts(
                        material_id=material_id,
                        material_name=material.original_filename,
                        requests_path=artifact_dir / "vision_requests.json",
                        responses_path=artifact_dir / "vision_responses.json",
                        output_dir=output_dir,
                        reviewer_id="system",
                        rationale=(
                            "Activated by instructor material upload"
                        ),
                        kb_version="course-material-v1",
                    )
                )
            except Exception:
                verified_kb_path = (
                    verified_kb_builder._build_fallback_verified_kb_from_pages(
                        material_id=material_id,
                        material_name=material.original_filename,
                        pages_path=artifact_dir / "pages.json",
                        output_dir=output_dir,
                        reviewer_id="system",
                        rationale=(
                            "Activated by instructor material upload"
                        ),
                        kb_version="course-material-v1",
                    )
                )

            activated_material_id = course_store_impl.activate(
                course_id=payload.course_id,
                class_session_id=payload.class_session_id,
                verified_kb_path=verified_kb_path,
            )

            return MaterialActivateResponse(
                material_id=activated_material_id,
                course_id=payload.course_id,
                class_session_id=payload.class_session_id,
                verified_kb_ref=str(
                    verified_kb_path.relative_to(
                        processing_service.work_root
                    )
                ),
                active_material_ids=list(
                    course_store_impl.active_material_ids(
                        course_id=payload.course_id,
                        class_session_id=payload.class_session_id,
                    )
                ),
            )
        except (MaterialStorageError, MaterialProcessingError, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc
        except FileNotFoundError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(exc),
            ) from exc

    return app


def _material_multimodal_mode() -> str:
    mode = os.getenv(
        "MATERIAL_MULTIMODAL_AGENT",
        "external",
    ).strip().lower()

    if mode not in {"none", "demo", "external", "gemini"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "MATERIAL_MULTIMODAL_AGENT must be "
                "'none', 'demo', 'external', or 'gemini'"
            ),
        )

    return mode


def _chat_attachment_agent_context(
    agent_context_factory: Callable[
        [str],
        AbstractContextManager[MultimodalAgent | None],
    ],
) -> AbstractContextManager[MultimodalAgent | None]:
    raw_mode = os.getenv("CHAT_ATTACHMENT_MULTIMODAL_AGENT")
    if raw_mode is None or not raw_mode.strip():
        return nullcontext(None)

    mode = raw_mode.strip().lower()
    if mode not in {"none", "demo", "external", "gemini"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "CHAT_ATTACHMENT_MULTIMODAL_AGENT must be "
                "'none', 'demo', 'external', or 'gemini'"
            ),
        )

    return agent_context_factory(mode)


def _material_processing_error_status(
    message: str,
) -> int:
    normalized = message.lower()

    if "not found" in normalized:
        return status.HTTP_404_NOT_FOUND

    if "unsupported material" in normalized:
        return status.HTTP_415_UNSUPPORTED_MEDIA_TYPE

    return status.HTTP_400_BAD_REQUEST


def _material_status_error_status(
    message: str,
) -> int:
    normalized = message.lower()

    if (
        "not found" in normalized
        or "invalid material_id" in normalized
    ):
        return status.HTTP_404_NOT_FOUND

    return status.HTTP_409_CONFLICT


def _persist_processing_failure_safely(
    *,
    processing_service: MaterialProcessingService,
    material_id: str,
    error_message: str,
) -> None:
    try:
        processing_service.persist_failed(
            material_id=material_id,
            error_message=error_message,
        )
    except MaterialProcessingError:
        pass


def _is_unsupported_media_error(
    message: str | None,
) -> bool:
    return bool(
        message
        and "unsupported material" in message.lower()
    )


def _external_provider_failure_message(
    error: MultimodalClientError,
) -> str:
    message = "External multimodal provider failed"
    if error.__class__.__module__ != (
        "src.agents.gemini_multimodal_agent"
    ):
        return message

    detail = str(error).strip()
    if not detail:
        return message

    return f"{message}: {detail}"


def _to_material_process_api_response(
    *,
    processing_response: MaterialProcessingResponse,
    work_root: Path,
) -> MaterialProcessAPIResponse:
    assets_manifest = Path(
        processing_response.assets_manifest_path
    )

    return MaterialProcessAPIResponse(
        material_id=processing_response.material_id,
        file_type=processing_response.file_type,
        processing_status=processing_response.status,
        total_pages=processing_response.total_pages,
        total_assets=_read_total_assets(assets_manifest),
        total_vision_requests=(
            processing_response.total_vision_requests
        ),
        total_vision_responses=(
            processing_response.total_vision_responses
        ),
        verified_count=processing_response.verified_count,
        needs_review_count=(
            processing_response.needs_review_count
        ),
        rejected_count=processing_response.rejected_count,
        pages_manifest_ref=_artifact_ref(
            processing_response.pages_manifest_path,
            work_root,
        ),
        assets_manifest_ref=_artifact_ref(
            processing_response.assets_manifest_path,
            work_root,
        ),
        vision_requests_ref=_artifact_ref(
            processing_response.vision_requests_path,
            work_root,
        ),
        vision_responses_ref=_optional_artifact_ref(
            processing_response.vision_responses_path,
            work_root,
        ),
        vision_verifications_ref=_optional_artifact_ref(
            processing_response.vision_verifications_path,
            work_root,
        ),
        error=processing_response.error,
    )


def _read_total_assets(
    assets_manifest_path: Path,
) -> int:
    try:
        payload = json.loads(
            assets_manifest_path.read_text(
                encoding="utf-8"
            )
        )
        total_assets = payload.get("total_assets", 0)

        if isinstance(total_assets, int) and total_assets >= 0:
            return total_assets

    except Exception:
        pass

    return 0


def _optional_artifact_ref(
    path: str | None,
    work_root: Path,
) -> str | None:
    if path is None:
        return None

    return _artifact_ref(path, work_root)


def _artifact_ref(
    path: str,
    work_root: Path,
) -> str:
    resolved_path = Path(path).resolve()
    resolved_root = work_root.resolve()

    try:
        relative_path = resolved_path.relative_to(
            resolved_root
        )
    except ValueError:
        return resolved_path.name

    return relative_path.as_posix()
