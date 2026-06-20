"""Provider-independent LLM client abstractions."""

from repopilot.llm.client import LLMClient
from repopilot.llm.factory import (
    LLMProviderConfigurationError,
    create_configured_llm_client,
)
from repopilot.llm.fake import FakeLLMClient
from repopilot.llm.models import LLMMessage, LLMRequest, LLMResponse, LLMUsage
from repopilot.llm.openai_client import (
    DEFAULT_OPENAI_MODEL,
    OpenAIConfigurationError,
    OpenAILLMClient,
    OpenAIProviderError,
)
from repopilot.llm.openrouter_client import (
    DEFAULT_OPENROUTER_MODEL,
    OpenRouterConfigurationError,
    OpenRouterLLMClient,
    OpenRouterLLMError,
)

__all__ = [
    "DEFAULT_OPENAI_MODEL",
    "DEFAULT_OPENROUTER_MODEL",
    "FakeLLMClient",
    "LLMClient",
    "LLMMessage",
    "LLMProviderConfigurationError",
    "LLMRequest",
    "LLMResponse",
    "LLMUsage",
    "OpenAIConfigurationError",
    "OpenAILLMClient",
    "OpenAIProviderError",
    "OpenRouterConfigurationError",
    "OpenRouterLLMClient",
    "OpenRouterLLMError",
    "create_configured_llm_client",
]
