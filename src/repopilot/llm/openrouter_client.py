from __future__ import annotations

import os
from typing import Any

import httpx

from repopilot.llm.models import LLMRequest, LLMResponse, LLMUsage

DEFAULT_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_OPENROUTER_MODEL = "~openai/gpt-latest"


class OpenRouterConfigurationError(ValueError):
    """Raised when OpenRouter client configuration is missing or invalid."""


class OpenRouterLLMError(RuntimeError):
    """Raised when an OpenRouter request or response cannot be handled."""


class OpenRouterLLMClient:
    """OpenRouter chat-completions adapter for RepoPilot's LLMClient protocol."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str = DEFAULT_OPENROUTER_MODEL,
        base_url: str = DEFAULT_OPENROUTER_BASE_URL,
        http_referer: str | None = None,
        app_title: str | None = None,
        timeout_seconds: float = 30.0,
        http_client: Any | None = None,
    ) -> None:
        cleaned_api_key = api_key.strip()
        if not cleaned_api_key:
            raise OpenRouterConfigurationError("OPENROUTER_API_KEY is required")

        cleaned_model = model.strip()
        if not cleaned_model:
            raise OpenRouterConfigurationError("OpenRouter model must not be empty")

        cleaned_base_url = base_url.strip().rstrip("/")
        if not cleaned_base_url:
            raise OpenRouterConfigurationError("OpenRouter base URL must not be empty")

        self.api_key = cleaned_api_key
        self.model = cleaned_model
        self.base_url = cleaned_base_url
        self.http_referer = _clean_optional_header(http_referer)
        self.app_title = _clean_optional_header(app_title)
        self.timeout_seconds = timeout_seconds
        self._http_client = http_client

    @classmethod
    def from_environment(cls) -> OpenRouterLLMClient:
        """Create a client from OpenRouter environment variables."""
        api_key = os.getenv("OPENROUTER_API_KEY", "")
        model = os.getenv("OPENROUTER_MODEL", DEFAULT_OPENROUTER_MODEL)
        base_url = os.getenv("OPENROUTER_BASE_URL", DEFAULT_OPENROUTER_BASE_URL)
        http_referer = os.getenv("OPENROUTER_HTTP_REFERER")
        app_title = os.getenv("OPENROUTER_APP_TITLE")

        return cls(
            api_key=api_key,
            model=model,
            base_url=base_url,
            http_referer=http_referer,
            app_title=app_title,
        )

    def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate text through OpenRouter's OpenAI-compatible chat API."""
        try:
            response_data = self._post_chat_completion(request)
        except httpx.HTTPStatusError as error:
            status_code = error.response.status_code
            raise OpenRouterLLMError(
                f"OpenRouter request failed with status {status_code}"
            ) from error
        except httpx.HTTPError as error:
            raise OpenRouterLLMError("OpenRouter request failed") from error
        except ValueError as error:
            raise OpenRouterLLMError(
                "OpenRouter response was not valid JSON"
            ) from error

        return _parse_openrouter_response(response_data, fallback_model=request.model)

    def _post_chat_completion(self, request: LLMRequest) -> dict[str, Any]:
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

        if self._http_client is not None:
            response = self._http_client.post(
                self._chat_completions_url(),
                headers=self._headers(),
                json=payload,
            )
            response.raise_for_status()
            return response.json()

        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.post(
                self._chat_completions_url(),
                headers=self._headers(),
                json=payload,
            )
            response.raise_for_status()
            return response.json()

    def _headers(self) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if self.http_referer is not None:
            headers["HTTP-Referer"] = self.http_referer
        if self.app_title is not None:
            headers["X-OpenRouter-Title"] = self.app_title
        return headers

    def _chat_completions_url(self) -> str:
        return f"{self.base_url}/chat/completions"


def _clean_optional_header(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned_value = value.strip()
    return cleaned_value or None


def _parse_openrouter_response(
    response_data: dict[str, Any],
    *,
    fallback_model: str,
) -> LLMResponse:
    try:
        choices = response_data["choices"]
        first_choice = choices[0]
        content = first_choice["message"]["content"]
    except (KeyError, IndexError, TypeError) as error:
        raise OpenRouterLLMError(
            "OpenRouter response did not include choices[0].message.content"
        ) from error

    if not isinstance(content, str):
        raise OpenRouterLLMError("OpenRouter response content was not text")

    model = response_data.get("model")
    if not isinstance(model, str) or not model.strip():
        model = fallback_model

    return LLMResponse(
        content=content,
        model=model,
        usage=_parse_usage(response_data.get("usage")),
    )


def _parse_usage(usage_data: object) -> LLMUsage | None:
    if not isinstance(usage_data, dict):
        return None

    input_tokens = usage_data.get("prompt_tokens", usage_data.get("input_tokens"))
    output_tokens = usage_data.get(
        "completion_tokens",
        usage_data.get("output_tokens"),
    )

    return LLMUsage(
        input_tokens=_optional_int(input_tokens),
        output_tokens=_optional_int(output_tokens),
    )


def _optional_int(value: object) -> int | None:
    if isinstance(value, int):
        return value
    return None
