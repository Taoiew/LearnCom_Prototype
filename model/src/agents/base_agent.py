"""Base agent interface for LearnCom."""

from dataclasses import dataclass
from typing import Any


@dataclass
class AgentResult:
    """Simple container for agent outputs."""

    output: str
    metadata: dict[str, Any] | None = None


class BaseAgent:
    """Base class for all agents in the project."""

    name: str = "base_agent"

    def run(self, prompt: str) -> AgentResult:
        return AgentResult(output=prompt)
