from __future__ import annotations

import httpx
import pytest

from repopilot.llm.models import LLMMessage, LLMRequest
from repopilot.llm.openrouter_client import (
    DEFAULT_OPENROUTER_MODEL,
    OpenRouterConfigurationError,
    OpenRouterLLMClient,
    OpenRouterLLMError,
)


def test_from_environment_requires_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    with pytest.raises(OpenRouterConfigurationError, match="OPENROUTER_API_KEY"):
        OpenRouterLLMClient.from_environment()


def test_from_environment_uses_default_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.delenv("OPENROUTER_MODEL", raising=False)

    client = OpenRouterLLMClient.from_environment()

    assert client.model == DEFAULT_OPENROUTER_MODEL


def test_from_environment_reads_optional_headers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("OPENROUTER_MODEL", "openrouter/custom")
    monkeypatch.setenv("OPENROUTER_HTTP_REFERER", "https://example.test")
    monkeypatch.setenv("OPENROUTER_APP_TITLE", "RepoPilot Tests")

    client = OpenRouterLLMClient.from_environment()

    assert client.model == "openrouter/custom"
    assert client.http_referer == "https://example.test"
    assert client.app_title == "RepoPilot Tests"


def test_generate_posts_chat_completion_request() -> None:
    http_client = FakeHttpClient(
        FakeResponse(
            {
                "model": "openrouter/custom",
                "choices": [{"message": {"content": "hello"}}],
            }
        )
    )
    client = OpenRouterLLMClient(
        api_key="secret-key",
        model="openrouter/custom",
        http_referer="https://example.test",
        app_title="RepoPilot",
        http_client=http_client,
    )

    response = client.generate(make_request())

    assert response.content == "hello"
    assert response.model == "openrouter/custom"
    assert http_client.last_url == "https://openrouter.ai/api/v1/chat/completions"
    assert http_client.last_headers["Authorization"] == "Bearer secret-key"
    assert http_client.last_headers["HTTP-Referer"] == "https://example.test"
    assert http_client.last_headers["X-OpenRouter-Title"] == "RepoPilot"
    assert http_client.last_json["model"] == "openrouter/custom"
    assert http_client.last_json["temperature"] == 0.1
    assert http_client.last_json["max_tokens"] == 200
    assert http_client.last_json["messages"] == [
        {"role": "system", "content": "Be concise."},
        {"role": "user", "content": "Say hello."},
    ]


def test_generate_populates_usage_when_available() -> None:
    http_client = FakeHttpClient(
        FakeResponse(
            {
                "choices": [{"message": {"content": "hello"}}],
                "usage": {"prompt_tokens": 4, "completion_tokens": 2},
            }
        )
    )
    client = OpenRouterLLMClient(api_key="secret-key", http_client=http_client)

    response = client.generate(make_request())

    assert response.usage is not None
    assert response.usage.input_tokens == 4
    assert response.usage.output_tokens == 2


def test_generate_falls_back_to_requested_model_when_response_omits_model() -> None:
    http_client = FakeHttpClient(
        FakeResponse({"choices": [{"message": {"content": "hello"}}]})
    )
    client = OpenRouterLLMClient(api_key="secret-key", http_client=http_client)

    response = client.generate(make_request())

    assert response.model == "openrouter/custom"


def test_generate_rejects_invalid_response_shape() -> None:
    http_client = FakeHttpClient(FakeResponse({"choices": []}))
    client = OpenRouterLLMClient(api_key="secret-key", http_client=http_client)

    with pytest.raises(OpenRouterLLMError, match="choices"):
        client.generate(make_request())


def test_generate_wraps_http_errors_without_leaking_api_key() -> None:
    http_client = FakeHttpClient(FakeResponse({}, status_code=401))
    client = OpenRouterLLMClient(api_key="secret-key", http_client=http_client)

    with pytest.raises(OpenRouterLLMError) as error_info:
        client.generate(make_request())

    assert "401" in str(error_info.value)
    assert "secret-key" not in str(error_info.value)


def test_generate_wraps_invalid_json() -> None:
    http_client = FakeHttpClient(FakeResponse(ValueError("bad json")))
    client = OpenRouterLLMClient(api_key="secret-key", http_client=http_client)

    with pytest.raises(OpenRouterLLMError, match="not valid JSON"):
        client.generate(make_request())


def make_request() -> LLMRequest:
    return LLMRequest(
        messages=[
            LLMMessage(role="system", content="Be concise."),
            LLMMessage(role="user", content="Say hello."),
        ],
        model="openrouter/custom",
        temperature=0.1,
        max_tokens=200,
    )


class FakeHttpClient:
    def __init__(self, response: FakeResponse) -> None:
        self.response = response
        self.last_url: str | None = None
        self.last_headers: dict[str, str] = {}
        self.last_json: dict[str, object] = {}

    def post(
        self,
        url: str,
        *,
        headers: dict[str, str],
        json: dict[str, object],
    ) -> FakeResponse:
        self.last_url = url
        self.last_headers = headers
        self.last_json = json
        return self.response


class FakeResponse:
    def __init__(
        self,
        data: dict[str, object] | ValueError,
        *,
        status_code: int = 200,
    ) -> None:
        self.data = data
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            request = httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions")
            response = httpx.Response(self.status_code, request=request)
            raise httpx.HTTPStatusError(
                "HTTP error",
                request=request,
                response=response,
            )

    def json(self) -> dict[str, object]:
        if isinstance(self.data, ValueError):
            raise self.data
        return self.data
