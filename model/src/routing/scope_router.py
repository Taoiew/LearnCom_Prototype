from dataclasses import dataclass

from schemas.model_contract import ScopeDecision


@dataclass(frozen=True)
class RoutingInput:
    question: str
    material_score: float
    course_relevance_score: float
    unsafe: bool = False


@dataclass(frozen=True)
class RoutingResult:
    decision: ScopeDecision
    reason: str


class ScopeRouter:
    def __init__(
        self,
        material_threshold: float = 0.70,
        course_threshold: float = 0.60,
    ) -> None:
        self.material_threshold = material_threshold
        self.course_threshold = course_threshold

    def route(self, data: RoutingInput) -> RoutingResult:
        if data.unsafe:
            return RoutingResult(
                decision=ScopeDecision.UNSAFE,
                reason="คำถามถูกตรวจพบว่าอาจไม่ปลอดภัย",
            )

        if data.material_score >= self.material_threshold:
            return RoutingResult(
                decision=ScopeDecision.IN_MATERIAL,
                reason="พบเนื้อหาที่เกี่ยวข้องเพียงพอใน Material",
            )

        if data.course_relevance_score >= self.course_threshold:
            return RoutingResult(
                decision=ScopeDecision.COURSE_RELATED_OUTSIDE_MATERIAL,
                reason="คำถามเกี่ยวข้องกับวิชา แต่ Material ยังไม่เพียงพอ",
            )

        return RoutingResult(
            decision=ScopeDecision.UNRELATED,
            reason="คำถามไม่เกี่ยวข้องกับขอบเขตของวิชา",
        )