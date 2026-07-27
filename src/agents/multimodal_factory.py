from collections.abc import Iterator
from contextlib import contextmanager

import httpx

from src.agents.multimodal_agent import (
    DemoMultimodalAgent,
    ExternalMultimodalAgent,
    MultimodalAgent,
)
from src.agents.multimodal_client import (
    MultimodalConfig,
    OpenAICompatibleMultimodalClient,
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

    if normalized_mode != "external":
        raise ValueError(
            f"Unsupported multimodal agent mode: {mode}"
        )

    config = MultimodalConfig.from_env()

    client = OpenAICompatibleMultimodalClient(
        config=config,
        http_client=http_client,
    )

    try:
        yield ExternalMultimodalAgent(
            client=client,
            agent_model=config.model,
        )
    finally:
        client.close()