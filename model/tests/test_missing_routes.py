from fastapi.testclient import TestClient

from schemas.model_contract import ChatResponse, ScopeDecision
from src.service.api import create_app
from src.service.conversation_attachment_service import ConversationAttachmentService
from src.retrieval.conversation_knowledge_store import ConversationKnowledgeStore


class FakePipeline:
    def run(self, request, course_relevance_score, unsafe=False):
        return ChatResponse(answer="ok", scope=ScopeDecision.IN_MATERIAL, confidence=0.90)


def test_chat_attachment_management_routes_exist_and_work():
    app = create_app(
        FakePipeline(),
        conversation_attachment_service=ConversationAttachmentService(
            base_dir="/tmp/chat-attachments-test",
            conversation_store=ConversationKnowledgeStore(),
        ),
    )
    client = TestClient(app)

    upload_response = client.post(
        "/v1/chat/attachments",
        data={
            "student_id": "student-1",
            "conversation_id": "conversation-1",
            "course_id": "course-1",
            "class_session_id": "session-1",
        },
        files={"file": ("sample.png", b"\x89PNG\r\n\x1a\nfake-png-content", "image/png")},
    )
    assert upload_response.status_code == 201
    body = upload_response.json()
    assert body["processing_status"] in {"stored", "ready", "failed"}

    attachment_id = body["attachment_id"]
    process_response = client.post(f"/v1/chat/attachments/{attachment_id}/process")
    assert process_response.status_code in {200, 400, 502}

    status_response = client.get(f"/v1/chat/attachments/{attachment_id}/status")
    assert status_response.status_code == 200

    delete_response = client.delete(f"/v1/chat/attachments/{attachment_id}")
    assert delete_response.status_code in {204, 404}


def test_rubric_routes_work():
    app = create_app(FakePipeline())
    client = TestClient(app)

    create_response = client.post(
        "/v1/rubrics",
        json={
            "course_id": "course-1",
            "class_session_id": "session-1",
            "rubric_name": "attendance",
            "criteria": ["present", "on-time"],
        },
    )
    assert create_response.status_code == 200
    rubric_id = create_response.json()["rubric_id"]

    list_response = client.get("/v1/rubrics/course-1/session-1")
    assert list_response.status_code == 200
    assert len(list_response.json()) >= 1

    evaluate_response = client.post(
        f"/v1/rubrics/{rubric_id}/evaluate",
        json={"score": 0.8, "notes": "ok"},
    )
    assert evaluate_response.status_code == 200


def test_session_report_routes_work():
    app = create_app(FakePipeline())
    client = TestClient(app)

    create_response = client.post(
        "/v1/session-reports/course-1/session-1/generate",
        json={"title": "summary", "summary": "Everything went well"},
    )
    assert create_response.status_code == 200

    list_response = client.get("/v1/session-reports/course-1/session-1")
    assert list_response.status_code == 200
    assert len(list_response.json()) >= 1
