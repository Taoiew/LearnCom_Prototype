from fastapi.testclient import TestClient

from schemas.model_contract import (
    ChatResponse,
    ScopeDecision,
)
from src.service.api import create_app


class FakePipeline:
    def run(
        self,
        request,
        course_relevance_score,
        unsafe=False,
    ):
        return ChatResponse(
            answer="คำตอบทดสอบ",
            scope=ScopeDecision.IN_MATERIAL,
            confidence=0.90,
        )


def test_health_endpoint():
    app = create_app(FakePipeline())
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_chat_endpoint():
    app = create_app(FakePipeline())
    client = TestClient(app)

    response = client.post(
        "/v1/chat",
        json={
            "request": {
                "student_id": "student-001",
                "course_id": "course-001",
                "class_session_id": "session-001",
                "phase": "during_class",
                "question": "Gradient descent คืออะไร",
            },
            "course_relevance_score": 0.90,
            "unsafe": False,
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["answer"] == "คำตอบทดสอบ"
    assert body["scope"] == "in_material"
    assert body["confidence"] == 0.90