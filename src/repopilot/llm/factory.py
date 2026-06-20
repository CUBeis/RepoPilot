from __future__ import annotations

import os

from repopilot.llm.client import LLMClient
from repopilot.llm.openai_client import OpenAILLMClient
from repopilot.llm.openrouter_client import OpenRouterLLMClient

DEFAULT_LLM_PROVIDER = "openrouter"
SUPPORTED_LLM_PROVIDERS = {"openai", "openrouter"}


class LLMProviderConfigurationError(ValueError):
    """Raised when the configured LLM provider is not supported."""


def create_configured_llm_client() -> LLMClient:
    """Create the configured real LLM provider client."""
    provider = os.getenv("REPOPILOT_LLM_PROVIDER", DEFAULT_LLM_PROVIDER)
    normalized_provider = provider.strip().lower()

    if normalized_provider == "openai":
        return OpenAILLMClient.from_environment()
    if normalized_provider == "openrouter":
        return OpenRouterLLMClient.from_environment()

    supported = ", ".join(sorted(SUPPORTED_LLM_PROVIDERS))
    raise LLMProviderConfigurationError(
        "Unknown REPOPILOT_LLM_PROVIDER "
        f"'{provider}'. Expected one of: {supported}."
    )
