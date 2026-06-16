from pydantic import BaseModel, Field


class LLMMessage(BaseModel):
    """One provider-independent chat message."""

    role: str = Field(min_length=1)
    content: str


class LLMRequest(BaseModel):
    """Provider-independent request for plain text generation."""

    messages: list[LLMMessage] = Field(min_length=1)
    model: str = Field(min_length=1)
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, gt=0)


class LLMUsage(BaseModel):
    """Optional token usage metadata for an LLM response."""

    input_tokens: int | None = None
    output_tokens: int | None = None


class LLMResponse(BaseModel):
    """Provider-independent response from plain text generation."""

    content: str
    model: str
    usage: LLMUsage | None = None
