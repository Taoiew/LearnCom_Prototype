from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import httpx

from src.agents.multimodal_agent import (
    DemoMultimodalAgent,
    ExternalMultimodalAgent,
    MultimodalAgent,
)
from src.agents.gemini_multimodal_agent import (
    GeminiMultimodalClient,
    GeminiMultimodalConfig,
)


GEMINI_PROMPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "prompts"
    / "gemini_multimodal_extraction_v1.txt"
)


@contextmanager
def multimodal_agent_context(
    mode: str,
    http_client: httpx.Client | None = None,
) -> Iterator[MultimodalAgent | None]:
    normalized_mode = mode.strip().lower()

    if normalized_mode == "none":
        yield None
        return

    if normalized_mode == "demo":
        yield DemoMultimodalAgent()
        return

    if normalized_mode not in {"external", "gemini"}:
        raise ValueError(
            f"Unsupported multimodal agent mode: {mode}"
        )

    config = GeminiMultimodalConfig.from_env()

    client = GeminiMultimodalClient(
        config=config,
        http_client=http_client,
    )

    try:
        yield ExternalMultimodalAgent(
            client=client,
            agent_model=config.model,
            system_prompt=_load_gemini_prompt(),
        )
    finally:
        client.close()


def _load_gemini_prompt() -> str:
    return GEMINI_PROMPT_PATH.read_text(encoding="utf-8").strip()
