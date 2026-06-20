from __future__ import annotations

import os
from typing import Any

from repopilot.llm.models import LLMRequest, LLMResponse, LLMUsage

DEFAULT_OPENAI_MODEL = "gpt-5.5"


class OpenAIConfigurationError(ValueError):
    """Raised when direct OpenAI client configuration is missing or invalid."""


class OpenAIProviderError(RuntimeError):
    """Raised when a direct OpenAI request or response cannot be handled."""


class OpenAILLMClient:
    """Direct OpenAI chat-completions adapter for RepoPilot's LLMClient protocol."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str = DEFAULT_OPENAI_MODEL,
        timeout_seconds: float = 30.0,
        sdk_client: Any | None = None,
    ) -> None:
        cleaned_api_key = api_key.strip()
        if not cleaned_api_key:
            raise OpenAIConfigurationError("OPENAI_API_KEY is required")

        cleaned_model = model.strip()
        if not cleaned_model:
            raise OpenAIConfigurationError("OpenAI model must not be empty")

        self.api_key = cleaned_api_key
        self.model = cleaned_model
        self.timeout_seconds = timeout_seconds
        self._sdk_client = sdk_client or _create_sdk_client(
            api_key=cleaned_api_key,
            timeout_seconds=timeout_seconds,
        )

    @classmethod
    def from_environment(
        cls,
        *,
        sdk_client: Any | None = None,
    ) -> OpenAILLMClient:
        """Create a direct OpenAI client from environment variables."""
        api_key = os.getenv("OPENAI_API_KEY", "")
        model = os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL)
        return cls(api_key=api_key, model=model, sdk_client=sdk_client)

    def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate text through OpenAI chat completions."""
        payload: dict[str, Any] = {
            "model": request.model,
            "messages": [
                {"role": message.role, "content": message.content}
                for message in request.messages
            ],
            "temperature": request.temperature,
        }
        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens

        try:
            response = self._sdk_client.chat.completions.create(**payload)
        except Exception as error:
            raise OpenAIProviderError("OpenAI request failed") from error

        return _parse_openai_response(response, fallback_model=request.model)


def _create_sdk_client(*, api_key: str, timeout_seconds: float) -> Any:
    try:
        from openai import OpenAI
    except ImportError as error:
        raise OpenAIConfigurationError(
            "The openai package is required for REPOPILOT_LLM_PROVIDER=openai"
        ) from error

    return OpenAI(api_key=api_key, timeout=timeout_seconds)


def _parse_openai_response(response: object, *, fallback_model: str) -> LLMResponse:
    choices = _get_value(response, "choices")
    first_choice = _first_item(choices)
    message = _get_value(first_choice, "message")
    content = _get_value(message, "content")
    text_content = _extract_text_content(content)
    if text_content is None:
        raise OpenAIProviderError("OpenAI response content was not text")

    model = _get_value(response, "model")
    if not isinstance(model, str) or not model.strip():
        model = fallback_model

    return LLMResponse(
        content=text_content,
        model=model,
        usage=_parse_usage(_get_value(response, "usage")),
    )


def _extract_text_content(content: object) -> str | None:
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            text = _get_value(item, "text")
            if isinstance(text, str):
                parts.append(text)
                continue

            nested_text = _get_value(_get_value(item, "text"), "value")
            if isinstance(nested_text, str):
                parts.append(nested_text)

        if parts:
            return "".join(parts)

    return None


def _parse_usage(usage_data: object) -> LLMUsage | None:
    if usage_data is None:
        return None

    input_tokens = _get_value(usage_data, "prompt_tokens")
    if input_tokens is None:
        input_tokens = _get_value(usage_data, "input_tokens")

    output_tokens = _get_value(usage_data, "completion_tokens")
    if output_tokens is None:
        output_tokens = _get_value(usage_data, "output_tokens")

    return LLMUsage(
        input_tokens=_optional_int(input_tokens),
        output_tokens=_optional_int(output_tokens),
    )


def _get_value(source: object, name: str) -> object:
    if isinstance(source, dict):
        return source.get(name)
    return getattr(source, name, None)


def _first_item(value: object) -> object:
    if isinstance(value, list) and value:
        return value[0]
    if isinstance(value, tuple) and value:
        return value[0]
    raise OpenAIProviderError("OpenAI response did not include choices[0]")


def _optional_int(value: object) -> int | None:
    if isinstance(value, int):
        return value
    return None
