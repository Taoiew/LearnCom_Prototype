import pytest

from schemas.model_contract import ScopeDecision
from src.routing.scope_router import RoutingInput, ScopeRouter


@pytest.fixture
def router() -> ScopeRouter:
    return ScopeRouter()


@pytest.mark.parametrize(
    ("routing_input", "expected"),
    [
        (
            RoutingInput("อธิบายหัวข้อในสไลด์", 0.90, 0.95),
            ScopeDecision.IN_MATERIAL,
        ),
        (
            RoutingInput("ขอตัวอย่างเพิ่มเติม", 0.30, 0.85),
            ScopeDecision.COURSE_RELATED_OUTSIDE_MATERIAL,
        ),
        (
            RoutingInput("วันนี้กินอะไรดี", 0.10, 0.15),
            ScopeDecision.UNRELATED,
        ),
        (
            RoutingInput("คำถามไม่ปลอดภัย", 0.90, 0.90, unsafe=True),
            ScopeDecision.UNSAFE,
        ),
    ],
)
def test_scope_router(routing_input, expected, router):
    result = router.route(routing_input)
    assert result.decision == expected
    assert result.reason