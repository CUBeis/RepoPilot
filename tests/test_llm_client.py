import pytest
from pydantic import ValidationError

from repopilot.llm import FakeLLMClient, LLMMessage, LLMRequest, LLMResponse, LLMUsage
from repopilot.llm.client import LLMClient


def make_request() -> LLMRequest:
    return LLMRequest(
        messages=[
            LLMMessage(role="system", content="You are RepoPilot."),
            LLMMessage(role="user", content="Create a plan."),
        ],
        model="fake-planner",
    )


def test_llm_request_accepts_valid_messages() -> None:
    request = make_request()

    assert request.model == "fake-planner"
    assert request.temperature == 0.0
    assert request.messages[0].role == "system"
    assert request.messages[1].content == "Create a plan."


def test_llm_response_stores_content_and_model() -> None:
    response = LLMResponse(
        content="A deterministic response.",
        model="fake-planner",
        usage=LLMUsage(input_tokens=3, output_tokens=3),
    )

    assert response.content == "A deterministic response."
    assert response.model == "fake-planner"
    assert response.usage is not None
    assert response.usage.input_tokens == 3


def test_fake_llm_client_returns_deterministic_content() -> None:
    client = FakeLLMClient("fixed plan")

    response = client.generate(make_request())

    assert response.content == "fixed plan"
    assert response.model == "fake-planner"


def test_fake_llm_client_stores_last_request() -> None:
    client = FakeLLMClient("fixed plan")
    request = make_request()

    client.generate(request)

    assert client.last_request == request


def test_fake_llm_client_can_be_called_multiple_times_deterministically() -> None:
    client = FakeLLMClient("same response")
    request = make_request()

    first_response = client.generate(request)
    second_response = client.generate(request)

    assert first_response == second_response


def test_fake_token_usage_is_stable() -> None:
    client = FakeLLMClient("fixed response")
    request = make_request()

    first_response = client.generate(request)
    second_response = client.generate(request)

    assert first_response.usage == second_response.usage
    assert first_response.usage is not None
    assert first_response.usage.input_tokens == 6
    assert first_response.usage.output_tokens == 2


def test_fake_token_usage_can_be_disabled() -> None:
    client = FakeLLMClient("fixed response", estimate_usage=False)

    response = client.generate(make_request())

    assert response.usage is None


def test_invalid_temperature_is_rejected_clearly() -> None:
    with pytest.raises(ValidationError, match="greater than or equal to 0"):
        LLMRequest(
            messages=[LLMMessage(role="user", content="Hello")],
            model="fake-planner",
            temperature=-0.1,
        )


def test_fake_client_satisfies_llm_client_protocol_shape() -> None:
    client: LLMClient = FakeLLMClient("fixed response")

    response = client.generate(make_request())

    assert response.content == "fixed response"
