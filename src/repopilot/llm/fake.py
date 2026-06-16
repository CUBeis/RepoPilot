from repopilot.llm.models import LLMRequest, LLMResponse, LLMUsage


class FakeLLMClient:
    """Deterministic LLM client for tests and local development."""

    def __init__(
        self,
        fixed_response: str,
        *,
        estimate_usage: bool = True,
    ) -> None:
        self.fixed_response = fixed_response
        self.estimate_usage = estimate_usage
        self.last_request: LLMRequest | None = None

    def generate(self, request: LLMRequest) -> LLMResponse:
        """Return the configured fixed response for every request."""
        self.last_request = request
        return LLMResponse(
            content=self.fixed_response,
            model=request.model,
            usage=self._build_usage(request),
        )

    def _build_usage(self, request: LLMRequest) -> LLMUsage | None:
        if not self.estimate_usage:
            return None

        input_text = " ".join(message.content for message in request.messages)
        return LLMUsage(
            input_tokens=_estimate_word_tokens(input_text),
            output_tokens=_estimate_word_tokens(self.fixed_response),
        )


def _estimate_word_tokens(text: str) -> int:
    return len(text.split())
