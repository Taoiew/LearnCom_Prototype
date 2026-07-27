import httpx
import pytest

from src.agents.multimodal_agent import (
    DemoMultimodalAgent,
    ExternalMultimodalAgent,
)
from src.agents.gemini_multimodal_agent import (
    GeminiMultimodalConfigurationError,
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
        "GEMINI_API_BASE_URL",
        "https://generativelanguage.googleapis.com/v1beta",
    )
    monkeypatch.setenv(
        "GEMINI_VISION_MODEL",
        "gemini-test-model",
    )
    monkeypatch.setenv(
        "GEMINI_API_KEY",
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
        base_url="https://generativelanguage.googleapis.com/v1beta/",
    ) as http_client:
        with multimodal_agent_context(
            mode="external",
            http_client=http_client,
        ) as agent:
            assert isinstance(
                agent,
                ExternalMultimodalAgent,
            )
            assert agent.agent_model == "gemini-test-model"


def test_factory_supports_gemini_alias(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GEMINI_VISION_MODEL", "gemini-test-model")

    with httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json={})
        ),
        base_url="https://generativelanguage.googleapis.com/v1beta/",
    ) as http_client:
        with multimodal_agent_context(
            mode="gemini",
            http_client=http_client,
        ) as agent:
            assert isinstance(agent, ExternalMultimodalAgent)
            assert agent.agent_model == "gemini-test-model"


def test_factory_external_without_api_key_fails_fast(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("GEMINI_VISION_MODEL", "gemini-test-model")

    with pytest.raises(
        GeminiMultimodalConfigurationError,
        match="GEMINI_API_KEY",
    ):
        with multimodal_agent_context("external"):
            pass


def test_factory_rejects_unknown_mode() -> None:
    with pytest.raises(
        ValueError,
        match="Unsupported multimodal agent mode",
    ):
        with multimodal_agent_context("unknown"):
            pass
