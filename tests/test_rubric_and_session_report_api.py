from pathlib import Path

from fastapi.testclient import TestClient

from schemas.model_contract import (
    ChatResponse,
    ScopeDecision,
)
from src.service.api import create_app
from src.service.rubric_service import RubricService, RubricStore
from src.service.session_analytics_service import SessionAnalyticsService


class FakePipeline:
    def run(self, request, course_relevance_score, unsafe=False):
        return ChatResponse(
            answer="Grounded answer",
            scope=ScopeDecision.IN_MATERIAL,
            confidence=0.8,
            learning_signals=[
                {
                    "topic": "IAM scenario",
                    "signal_type": "misconception",
                    "severity": 0.7,
                    "explanation": "Needs practical application",
                }
            ],
        )


def _client(tmp_path: Path) -> TestClient:
    return TestClient(
        create_app(
            pipeline=FakePipeline(),
            rubric_service=RubricService(
                store=RubricStore(tmp_path / "rubrics")
            ),
            analytics_service=SessionAnalyticsService(
                tmp_path / "analytics"
            ),
        )
    )


def test_create_evaluate_and_report(tmp_path: Path) -> None:
    client = _client(tmp_path)
    rubric_response = client.post(
        "/v1/rubrics",
        json={
            "course_id": "CS332",
            "class_session_id": "week-2",
            "title": "S3 application rubric",
            "description": "Assess scenario reasoning",
            "criteria": [
                {
                    "criterion_id": "iam",
                    "title": "IAM application",
                    "description": "Apply IAM to a real scenario",
                    "weight": 1.0,
                    "levels": [
                        {"label": "Basic", "score": 1, "description": "Limited"},
                        {"label": "Good", "score": 4, "description": "Accurate"},
                    ],
                }
            ],
        },
    )
    assert rubric_response.status_code == 201
    rubric_id = rubric_response.json()["rubric_id"]

    evaluation = client.post(
        f"/v1/rubrics/{rubric_id}/evaluate",
        json={
            "student_id": "student-1",
            "submission_text": "Apply IAM policy to the scenario",
            "evidence": ["IAM policy statement"],
        },
    )
    assert evaluation.status_code == 200
    assert evaluation.json()["rubric_id"] == rubric_id

    chat = client.post(
        "/v1/chat",
        json={
            "request": {
                "student_id": "student-1",
                "course_id": "CS332",
                "class_session_id": "week-2",
                "phase": "during_class",
                "question": "How should IAM be applied?",
                "conversation_id": "c-1",
            },
            "course_relevance_score": 0.9,
            "unsafe": False,
        },
    )
    assert chat.status_code == 200

    report = client.post(
        "/v1/session-reports/CS332/week-2/generate"
    )
    assert report.status_code == 200
    body = report.json()
    assert body["total_interactions"] == 1
    assert body["unique_students"] == 1
    assert body["at_risk_count"] == 1
    assert body["common_issues"] == ["IAM scenario"]
    assert body["rubric_summary"]["evaluation_count"] == 1.0


def test_upload_text_rubric(tmp_path: Path) -> None:
    client = _client(tmp_path)
    response = client.post(
        "/v1/rubrics/upload",
        data={
            "course_id": "CS332",
            "class_session_id": "week-2",
            "title": "Imported rubric",
        },
        files={
            "file": (
                "rubric.txt",
                b"Accuracy\nScenario application\nClear explanation",
                "text/plain",
            )
        },
    )
    assert response.status_code == 201
    assert len(response.json()["criteria"]) == 3
