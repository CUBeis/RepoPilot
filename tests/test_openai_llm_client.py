from __future__ import annotations

import pytest

from repopilot.llm.factory import create_configured_llm_client
from repopilot.llm.models import LLMMessage, LLMRequest
from repopilot.llm.openai_client import (
    DEFAULT_OPENAI_MODEL,
    OpenAIConfigurationError,
    OpenAILLMClient,
    OpenAIProviderError,
)
from repopilot.llm.openrouter_client import OpenRouterLLMClient


def test_from_environment_requires_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(OpenAIConfigurationError, match="OPENAI_API_KEY"):
        OpenAILLMClient.from_environment(sdk_client=FakeOpenAISdkClient({}))


def test_from_environment_reads_api_key_and_default_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.delenv("OPENAI_MODEL", raising=False)

    client = OpenAILLMClient.from_environment(
        sdk_client=FakeOpenAISdkClient(make_response())
    )

    assert client.api_key == "test-openai-key"
    assert client.model == DEFAULT_OPENAI_MODEL


def test_from_environment_reads_custom_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-test")

    client = OpenAILLMClient.from_environment(
        sdk_client=FakeOpenAISdkClient(make_response())
    )

    assert client.model == "gpt-test"


def test_generate_sends_chat_completion_payload() -> None:
    sdk_client = FakeOpenAISdkClient(make_response(content="hello"))
    client = OpenAILLMClient(
        api_key="test-openai-key",
        model="gpt-test",
        sdk_client=sdk_client,
    )

    response = client.generate(make_request())

    assert response.content == "hello"
    assert response.model == "gpt-test-response"
    assert sdk_client.chat.completions.last_payload == {
        "model": "gpt-test",
        "messages": [
            {"role": "system", "content": "Be concise."},
            {"role": "user", "content": "Say hello."},
        ],
        "temperature": 0.2,
        "max_tokens": 200,
    }


def test_generate_populates_usage_when_available() -> None:
    client = OpenAILLMClient(
        api_key="test-openai-key",
        sdk_client=FakeOpenAISdkClient(make_response()),
    )

    response = client.generate(make_request())

    assert response.usage is not None
    assert response.usage.input_tokens == 5
    assert response.usage.output_tokens == 3


def test_generate_handles_list_text_content() -> None:
    response_data = make_response(content=[{"text": "hello"}, {"text": " world"}])
    client = OpenAILLMClient(
        api_key="test-openai-key",
        sdk_client=FakeOpenAISdkClient(response_data),
    )

    response = client.generate(make_request())

    assert response.content == "hello world"


def test_generate_rejects_non_text_content() -> None:
    response_data = make_response(content=[{"type": "image"}])
    client = OpenAILLMClient(
        api_key="test-openai-key",
        sdk_client=FakeOpenAISdkClient(response_data),
    )

    with pytest.raises(OpenAIProviderError, match="content was not text"):
        client.generate(make_request())


def test_provider_errors_are_clear_and_do_not_leak_api_key() -> None:
    sdk_client = FakeOpenAISdkClient(
        make_response(),
        error=RuntimeError("bad secret test-openai-key"),
    )
    client = OpenAILLMClient(
        api_key="test-openai-key",
        sdk_client=sdk_client,
    )

    with pytest.raises(OpenAIProviderError) as error_info:
        client.generate(make_request())

    assert str(error_info.value) == "OpenAI request failed"
    assert "test-openai-key" not in str(error_info.value)


def test_provider_factory_returns_openai_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected_client = OpenAILLMClient(
        api_key="test-openai-key",
        sdk_client=FakeOpenAISdkClient(make_response()),
    )
    monkeypatch.setenv("REPOPILOT_LLM_PROVIDER", "openai")
    monkeypatch.setattr(
        "repopilot.llm.factory.OpenAILLMClient.from_environment",
        staticmethod(lambda: expected_client),
    )

    client = create_configured_llm_client()

    assert client is expected_client


def test_provider_factory_returns_openrouter_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected_client = OpenRouterLLMClient(
        api_key="test-openrouter-key",
        http_client=object(),
    )
    monkeypatch.setenv("REPOPILOT_LLM_PROVIDER", "openrouter")
    monkeypatch.setattr(
        "repopilot.llm.factory.OpenRouterLLMClient.from_environment",
        staticmethod(lambda: expected_client),
    )

    client = create_configured_llm_client()

    assert client is expected_client


def test_provider_factory_rejects_unknown_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("REPOPILOT_LLM_PROVIDER", "unknown")

    with pytest.raises(ValueError, match="REPOPILOT_LLM_PROVIDER"):
        create_configured_llm_client()


def make_request() -> LLMRequest:
    return LLMRequest(
        messages=[
            LLMMessage(role="system", content="Be concise."),
            LLMMessage(role="user", content="Say hello."),
        ],
        model="gpt-test",
        temperature=0.2,
        max_tokens=200,
    )


def make_response(content: object = "hello") -> dict[str, object]:
    return {
        "model": "gpt-test-response",
        "choices": [{"message": {"content": content}}],
        "usage": {"prompt_tokens": 5, "completion_tokens": 3},
    }


class FakeOpenAISdkClient:
    def __init__(
        self,
        response: dict[str, object],
        *,
        error: Exception | None = None,
    ) -> None:
        self.chat = FakeChat(response=response, error=error)


class FakeChat:
    def __init__(
        self,
        *,
        response: dict[str, object],
        error: Exception | None,
    ) -> None:
        self.completions = FakeCompletions(response=response, error=error)


class FakeCompletions:
    def __init__(
        self,
        *,
        response: dict[str, object],
        error: Exception | None,
    ) -> None:
        self.response = response
        self.error = error
        self.last_payload: dict[str, object] | None = None

    def create(self, **payload: object) -> dict[str, object]:
        self.last_payload = payload
        if self.error is not None:
            raise self.error
        return self.response
