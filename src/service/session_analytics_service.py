import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock

from schemas.model_contract import ChatRequest, ChatResponse
from schemas.rubric_contract import RubricEvaluation, SessionReport


class SessionAnalyticsService:
    def __init__(self, root: str | Path = "data/session_analytics") -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()

    def record_chat(self, request: ChatRequest, response: ChatResponse) -> None:
        payload = {
            "type": "chat",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "request": request.model_dump(mode="json"),
            "response": response.model_dump(mode="json"),
        }
        self._append(request.course_id, request.class_session_id, payload)

    def record_evaluation(
        self,
        *,
        course_id: str,
        class_session_id: str,
        evaluation: RubricEvaluation,
    ) -> None:
        self._append(
            course_id,
            class_session_id,
            {
                "type": "rubric_evaluation",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "evaluation": evaluation.model_dump(mode="json"),
            },
        )

    def generate_report(self, course_id: str, class_session_id: str) -> SessionReport:
        events = self._read(course_id, class_session_id)
        chat_events = [item for item in events if item.get("type") == "chat"]
        evaluation_events = [item for item in events if item.get("type") == "rubric_evaluation"]

        students = {item["request"]["student_id"] for item in chat_events}
        confidences = [float(item["response"].get("confidence", 0)) for item in chat_events]
        severities: dict[str, list[float]] = defaultdict(list)
        issues: Counter[str] = Counter()
        for item in chat_events:
            for signal in item["response"].get("learning_signals", []):
                topic = str(signal.get("topic", "Unknown"))
                severity = float(signal.get("severity", 0))
                severities[item["request"]["student_id"]].append(severity)
                if severity >= 0.4:
                    issues[topic] += 1

        student_readiness: list[float] = []
        for student_id in students:
            values = severities.get(student_id, [])
            average_severity = sum(values) / len(values) if values else 0.0
            student_readiness.append(max(0.0, 100 * (1 - average_severity)))

        on_track = sum(value >= 70 for value in student_readiness)
        needs_review = sum(40 <= value < 70 for value in student_readiness)
        at_risk = sum(value < 40 for value in student_readiness)

        rubric_scores = [
            float(item["evaluation"].get("percentage", 0))
            for item in evaluation_events
        ]
        common_issues = [name for name, _ in issues.most_common(5)]
        suggested_focus = (
            f"Review {common_issues[0]} with a worked example at the start of the next session."
            if common_issues
            else "No recurring learning issue was detected from the available interactions."
        )
        now = datetime.now(timezone.utc)
        report_id = "report-" + hashlib.sha256(
            f"{course_id}:{class_session_id}:{now.isoformat()}".encode()
        ).hexdigest()[:16]
        report = SessionReport(
            report_id=report_id,
            course_id=course_id,
            class_session_id=class_session_id,
            generated_at=now,
            total_interactions=len(chat_events),
            unique_students=len(students),
            average_confidence=(sum(confidences) / len(confidences) if confidences else 0.0),
            average_readiness=(sum(student_readiness) / len(student_readiness) if student_readiness else 0.0),
            on_track_count=on_track,
            needs_review_count=needs_review,
            at_risk_count=at_risk,
            common_issues=common_issues,
            suggested_focus=suggested_focus,
            rubric_summary={
                "evaluation_count": float(len(rubric_scores)),
                "average_score": (sum(rubric_scores) / len(rubric_scores) if rubric_scores else 0.0),
            },
        )
        path = self._session_dir(course_id, class_session_id) / "latest_report.json"
        path.write_text(report.model_dump_json(indent=2) + "\n", encoding="utf-8")
        return report

    def get_latest_report(self, course_id: str, class_session_id: str) -> SessionReport:
        path = self._session_dir(course_id, class_session_id) / "latest_report.json"
        if not path.is_file():
            raise FileNotFoundError("Session report not found")
        return SessionReport.model_validate_json(path.read_text(encoding="utf-8"))

    def _append(self, course_id: str, class_session_id: str, payload: dict) -> None:
        directory = self._session_dir(course_id, class_session_id)
        path = directory / "events.jsonl"
        with self._lock, path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def _read(self, course_id: str, class_session_id: str) -> list[dict]:
        path = self._session_dir(course_id, class_session_id) / "events.jsonl"
        if not path.is_file():
            return []
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

    def _session_dir(self, course_id: str, class_session_id: str) -> Path:
        safe = lambda value: "".join(ch if ch.isalnum() or ch in "._-" else "-" for ch in value)
        directory = self.root / safe(course_id) / safe(class_session_id)
        directory.mkdir(parents=True, exist_ok=True)
        return directory
