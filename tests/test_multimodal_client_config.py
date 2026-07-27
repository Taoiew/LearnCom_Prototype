import pytest

from src.agents.multimodal_client import (
    MultimodalConfig,
    MultimodalConfigurationError,
)


def test_multimodal_config_loads_from_environment(
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
    monkeypatch.setenv(
        "EXTERNAL_MULTIMODAL_TIMEOUT_SECONDS",
        "45",
    )
    monkeypatch.setenv(
        "EXTERNAL_MULTIMODAL_MAX_IMAGE_BYTES",
        "5242880",
    )

    config = MultimodalConfig.from_env()

    assert config.base_url == (
        "https://provider.example/v1"
    )
    assert config.model == "vision-model"
    assert config.api_key == "test-key"
    assert config.timeout_seconds == 45.0
    assert config.max_image_bytes == 5 * 1024 * 1024


def test_multimodal_config_rejects_missing_model() -> None:
    with pytest.raises(
        MultimodalConfigurationError,
        match="model must not be empty",
    ):
        MultimodalConfig(
            base_url="https://provider.example/v1",
            model="",
        )


def test_multimodal_config_rejects_invalid_environment(
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
        "EXTERNAL_MULTIMODAL_TIMEOUT_SECONDS",
        "not-a-number",
    )

    with pytest.raises(
        MultimodalConfigurationError,
        match=(
            "EXTERNAL_MULTIMODAL_TIMEOUT_SECONDS "
            "must be a number"
        ),
    ):
        MultimodalConfig.from_env()