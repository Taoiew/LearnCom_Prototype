"""A simple example agent implementation."""

from .base_agent import AgentResult, BaseAgent


class SimpleAgent(BaseAgent):
    """Minimal agent that returns a formatted response."""

    name = "simple_agent"

    def run(self, prompt: str) -> AgentResult:
        return AgentResult(output=f"Processed: {prompt}")
