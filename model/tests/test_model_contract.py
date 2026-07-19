from schemas.model_contract import (
    ChatRequest,
    ChatResponse,
    LearningPhase,
    ScopeDecision,
)


def test_chat_contract():
    request = ChatRequest(
        student_id="student-001",
        course_id="course-001",
        class_session_id="session-001",
        phase=LearningPhase.PRE_CLASS,
        question="หัวข้อนี้มีแนวคิดสำคัญอะไรบ้าง",
    )

    response = ChatResponse(
        answer="ลองเริ่มจากอธิบายแนวคิดพื้นฐานที่คุณเข้าใจก่อน",
        scope=ScopeDecision.IN_MATERIAL,
        confidence=0.90,
    )

    assert request.phase == LearningPhase.PRE_CLASS
    assert response.scope == ScopeDecision.IN_MATERIAL
    assert response.used_external_agent is False