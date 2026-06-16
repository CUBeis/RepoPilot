from typing import Protocol

from repopilot.llm.models import LLMRequest, LLMResponse


class LLMClient(Protocol):
    """Protocol implemented by provider-specific LLM clients."""

    def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate plain text from a provider-independent request."""
        ...
