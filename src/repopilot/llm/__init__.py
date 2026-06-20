"""Provider-independent LLM client abstractions."""

from repopilot.llm.client import LLMClient
from repopilot.llm.fake import FakeLLMClient
from repopilot.llm.models import LLMMessage, LLMRequest, LLMResponse, LLMUsage
from repopilot.llm.openrouter_client import (
    DEFAULT_OPENROUTER_MODEL,
    OpenRouterConfigurationError,
    OpenRouterLLMClient,
    OpenRouterLLMError,
)

__all__ = [
    "DEFAULT_OPENROUTER_MODEL",
    "FakeLLMClient",
    "LLMClient",
    "LLMMessage",
    "LLMRequest",
    "LLMResponse",
    "LLMUsage",
    "OpenRouterConfigurationError",
    "OpenRouterLLMClient",
    "OpenRouterLLMError",
]
