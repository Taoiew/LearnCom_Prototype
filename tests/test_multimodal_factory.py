import httpx
import pytest

from src.agents.multimodal_agent import (
    DemoMultimodalAgent,
    ExternalMultimodalAgent,
)
from src.agents.multimodal_factory import (
    multimodal_agent_context,
)


def test_factory_returns_none_for_disabled_mode() -> None:
    with multimodal_agent_context("none") as agent:
        assert agent is None


def test_factory_returns_demo_agent() -> None:
    with multimodal_agent_context("demo") as agent:
        assert isinstance(
            agent,
            DemoMultimodalAgent,
        )


def test_factory_builds_external_agent_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "EXTERNAL_MULTIMODAL_BASE_URL",
        "https://provider.example/v1",
    )
    monkeypatch.setenv(
        "EXTERNAL_MULTIMODAL_MODEL",
        "vision-model",
    )
    monkeypatch.setenv(
        "EXTERNAL_MULTIMODAL_API_KEY",
        "test-key",
    )

    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={},
        )
    )

    with httpx.Client(
        transport=transport,
        base_url="https://provider.example/v1/",
    ) as http_client:
        with multimodal_agent_context(
            mode="external",
            http_client=http_client,
        ) as agent:
            assert isinstance(
                agent,
                ExternalMultimodalAgent,
            )
            assert agent.agent_model == "vision-model"


def test_factory_rejects_unknown_mode() -> None:
    with pytest.raises(
        ValueError,
        match="Unsupported multimodal agent mode",
    ):
        with multimodal_agent_context("unknown"):
            pass