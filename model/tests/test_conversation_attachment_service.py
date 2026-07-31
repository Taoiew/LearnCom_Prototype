from pathlib import Path

from fastapi.testclient import TestClient

from schemas.model_contract import ChatRequest, ChatResponse, LearningPhase, ScopeDecision
from src.retrieval.conversation_knowledge_store import ConversationKnowledgeStore
from src.agents.multimodal_client import MultimodalTransportError
from src.service.api import create_app
from src.service.conversation_attachment_service import ConversationAttachmentService


class FakePipeline:
    def run(self, request, course_relevance_score, unsafe=False):
        return ChatResponse(answer="attachment answer", scope=ScopeDecision.IN_MATERIAL, confidence=0.90)


class FailingBuildService:
    def build_for_material(self, **kwargs):
        raise AssertionError("Attachment should reuse the existing verified KB")


def test_conversation_attachment_service_builds_and_activates_conversation_kb(tmp_path: Path) -> None:
    service = ConversationAttachmentService(
        base_dir=tmp_path / "chat_attachments",
        conversation_store=ConversationKnowledgeStore(),
    )

    response = service.upload_attachment(
        student_id="student-a",
        conversation_id="conversation-a",
        course_id="course-001",
        class_session_id="session-001",
        filename="notes.png",
        content_type="image/png",
        content=b"\x89PNG\r\n\x1a\nfake-png-content",
    )

    assert response.processing_status == "ready"
    assert response.student_id == "student-a"
    assert response.conversation_id == "conversation-a"

    status = service.get_status(response.attachment_id)
    assert status.processing_status == "ready"

    results = service.conversation_store.search(
        student_id="student-a",
        conversation_id="conversation-a",
        query="notes",
        top_k=3,
    )
    assert results


def test_uploading_same_attachment_reuses_existing_verified_kb_after_restart(
    tmp_path: Path,
) -> None:
    base_dir = tmp_path / "chat_attachments"
    content = b"\x89PNG\r\n\x1a\nfake-png-content"

    first_service = ConversationAttachmentService(
        base_dir=base_dir,
        conversation_store=ConversationKnowledgeStore(),
    )
    first = first_service.upload_attachment(
        student_id="student-a",
        conversation_id="conversation-a",
        course_id="course-001",
        class_session_id="session-001",
        filename="notes.png",
        content_type="image/png",
        content=content,
    )

    restarted_service = ConversationAttachmentService(
        base_dir=base_dir,
        conversation_store=ConversationKnowledgeStore(),
        build_service=FailingBuildService(),
    )
    second = restarted_service.upload_attachment(
        student_id="student-a",
        conversation_id="conversation-a",
        course_id="course-001",
        class_session_id="session-001",
        filename="notes.png",
        content_type="image/png",
        content=content,
    )

    assert second.attachment_id == first.attachment_id
    assert second.processing_status == "ready"
    assert restarted_service.conversation_store.search(
        student_id="student-a",
        conversation_id="conversation-a",
        query="notes",
        top_k=1,
    )


def test_upload_recreates_missing_status_directory(tmp_path: Path) -> None:
    base_dir = tmp_path / "chat_attachments"
    service = ConversationAttachmentService(
        base_dir=base_dir,
        conversation_store=ConversationKnowledgeStore(),
    )

    status_dir = base_dir / "status"
    for status_file in status_dir.glob("*.json"):
        status_file.unlink()
    status_dir.rmdir()

    response = service.upload_attachment(
        student_id="student-a",
        conversation_id="conversation-a",
        course_id="course-001",
        class_session_id="session-001",
        filename="notes.png",
        content_type="image/png",
        content=b"\x89PNG\r\n\x1a\nfake-png-content",
        auto_process=False,
    )

    assert response.processing_status == "stored"
    assert (status_dir / f"{response.attachment_id}.json").is_file()


def test_chat_with_attachment_api_returns_attachment_and_chat(tmp_path: Path) -> None:
    app = create_app(
        pipeline=FakePipeline(),
        conversation_attachment_service=ConversationAttachmentService(
            base_dir=tmp_path / "chat_attachments",
            conversation_store=ConversationKnowledgeStore(),
        ),
    )
    client = TestClient(app)

    response = client.post(
        "/v1/chat/with-attachment",
        data={
            "request_json": ChatRequest(
                student_id="student-b",
                course_id="course-001",
                class_session_id="session-001",
                phase=LearningPhase.DURING_CLASS,
                question="What is in the attachment?",
                conversation_id="conversation-b",
            ).model_dump_json(),
            "course_relevance_score": "0.90",
            "unsafe": "false",
        },
        files={"file": ("sample.png", b"\x89PNG\r\n\x1a\nfake-png-content", "image/png")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["attachment"]["student_id"] == "student-b"
    assert body["chat"]["answer"] == "attachment answer"


def test_chat_with_attachment_api_reuses_ready_attachment_without_reprocessing(
    tmp_path: Path,
    monkeypatch,
) -> None:
    service = ConversationAttachmentService(
        base_dir=tmp_path / "chat_attachments",
        conversation_store=ConversationKnowledgeStore(),
    )
    content = b"\x89PNG\r\n\x1a\nfake-png-content"
    service.upload_attachment(
        student_id="student-b",
        conversation_id="conversation-b",
        course_id="course-001",
        class_session_id="session-001",
        filename="sample.png",
        content_type="image/png",
        content=content,
    )

    def fail_process(*args, **kwargs):
        raise AssertionError("Ready attachments should not be processed again")

    monkeypatch.setattr(service, "process_attachment", fail_process)
    app = create_app(
        pipeline=FakePipeline(),
        conversation_attachment_service=service,
    )
    client = TestClient(app)

    response = client.post(
        "/v1/chat/with-attachment",
        data={
            "request_json": ChatRequest(
                student_id="student-b",
                course_id="course-001",
                class_session_id="session-001",
                phase=LearningPhase.DURING_CLASS,
                question="What is in the attachment?",
                conversation_id="conversation-b",
            ).model_dump_json(),
            "course_relevance_score": "0.90",
            "unsafe": "false",
        },
        files={"file": ("sample.png", content, "image/png")},
    )

    assert response.status_code == 200
    assert response.json()["chat"]["answer"] == "attachment answer"


def test_chat_with_attachment_api_reports_processing_failure(
    tmp_path: Path,
    monkeypatch,
) -> None:
    service = ConversationAttachmentService(
        base_dir=tmp_path / "chat_attachments",
        conversation_store=ConversationKnowledgeStore(),
    )

    def fail_process(*args, **kwargs):
        raise Exception("synthetic attachment failure")

    monkeypatch.setattr(service, "process_attachment", fail_process)
    app = create_app(
        pipeline=FakePipeline(),
        conversation_attachment_service=service,
    )
    client = TestClient(app)

    response = client.post(
        "/v1/chat/with-attachment",
        data={
            "request_json": ChatRequest(
                student_id="student-b",
                course_id="course-001",
                class_session_id="session-001",
                phase=LearningPhase.DURING_CLASS,
                question="What is in the attachment?",
                conversation_id="conversation-b",
            ).model_dump_json(),
            "course_relevance_score": "0.90",
            "unsafe": "false",
        },
        files={"file": ("sample.png", b"\x89PNG\r\n\x1a\nfake-png-content", "image/png")},
    )

    assert response.status_code == 502
    assert response.json()["detail"] == (
        "Attachment processing failed: synthetic attachment failure"
    )


def test_process_chat_attachment_provider_failure_returns_502(
    tmp_path: Path,
    monkeypatch,
) -> None:
    service = ConversationAttachmentService(
        base_dir=tmp_path / "chat_attachments",
        conversation_store=ConversationKnowledgeStore(),
    )
    upload = service.upload_attachment(
        student_id="student-c",
        conversation_id="conversation-c",
        course_id="course-001",
        class_session_id="session-001",
        filename="notes.png",
        content_type="image/png",
        content=b"\x89PNG\r\n\x1a\nfake-png-content",
        auto_process=False,
    )

    def fail_process(*args, **kwargs):
        raise MultimodalTransportError(
            "Gemini Vision rate limit exceeded"
        )

    monkeypatch.setattr(
        service,
        "process_attachment",
        fail_process,
    )
    app = create_app(
        pipeline=FakePipeline(),
        conversation_attachment_service=service,
    )
    client = TestClient(app)

    response = client.post(
        f"/v1/chat/attachments/{upload.attachment_id}/process"
    )

    assert response.status_code == 502
    assert response.json()["detail"] == (
        "Gemini Vision rate limit exceeded"
    )
