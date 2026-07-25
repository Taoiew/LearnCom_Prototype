from pathlib import Path

from fastapi.testclient import TestClient

from schemas.model_contract import ChatRequest, ChatResponse, LearningPhase, ScopeDecision
from src.retrieval.conversation_knowledge_store import ConversationKnowledgeStore
from src.service.api import create_app
from src.service.conversation_attachment_service import ConversationAttachmentService


class FakePipeline:
    def run(self, request, course_relevance_score, unsafe=False):
        return ChatResponse(answer="attachment answer", scope=ScopeDecision.IN_MATERIAL, confidence=0.90)


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
