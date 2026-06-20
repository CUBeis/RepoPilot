# Learning Note 35: Direct OpenAI Provider Support

## What Was Built

This hotfix adds direct OpenAI provider support behind RepoPilot's existing
`LLMClient` abstraction.

RepoPilot can now choose between:

- `REPOPILOT_LLM_PROVIDER=openrouter`
- `REPOPILOT_LLM_PROVIDER=openai`

The `POST /agent/preview` endpoint uses that provider setting only when
`use_llm=true`.

## Why This Was Needed

OpenRouter and OpenAI are different providers. An OpenAI API key should be sent
only to OpenAI, not to OpenRouter.

Before this hotfix, the real-provider path was OpenRouter-only. Users who had a
direct OpenAI key needed a separate provider adapter so their key could be used
with OpenAI's API directly.

## Environment Variables

Direct OpenAI:

```powershell
$env:REPOPILOT_LLM_PROVIDER = "openai"
$env:OPENAI_API_KEY = "your-new-openai-key"
$env:OPENAI_MODEL = "gpt-5.5"
```

OpenRouter:

```powershell
$env:REPOPILOT_LLM_PROVIDER = "openrouter"
$env:OPENROUTER_API_KEY = "your-openrouter-key"
$env:OPENROUTER_MODEL = "~openai/gpt-latest"
```

Never commit real keys. If a key was pasted, shared, or committed, revoke it and
generate a new one.

## How Provider Selection Works

The new factory reads `REPOPILOT_LLM_PROVIDER`:

```text
openai -> OpenAILLMClient.from_environment()
openrouter -> OpenRouterLLMClient.from_environment()
```

Unknown providers raise a clear configuration error.

OpenRouter remains the default provider for backward compatibility.

## How The OpenAI Client Works

`OpenAILLMClient`:

- reads `OPENAI_API_KEY` and `OPENAI_MODEL`
- converts `LLMRequest.messages` into OpenAI chat messages
- calls the official OpenAI Python SDK
- parses text content into `LLMResponse.content`
- maps usage metadata when available
- raises `OpenAIConfigurationError` for missing configuration
- raises `OpenAIProviderError` for provider/API failures

The SDK import is lazy, so tests can inject fake SDK clients without making real
network calls.

## Robust Structured Output Handling

The LLM planner now accepts JSON wrapped in Markdown fences, such as a response
that starts with three backticks followed by `json` and ends with three
backticks.

If the LLM still returns invalid JSON, the agent preview falls back to the
deterministic planner. This keeps the Streamlit demo usable while preserving a
clear safety boundary.

## Safety Boundary

This hotfix does not add new agent actions.

The agent preview endpoint still does not:

- apply patches
- run commands
- write files
- generate repair approval requests
- start self-correction

It only builds context, creates a plan, and returns a bounded patch preview.

## Files Added Or Updated

### `src/repopilot/llm/openai_client.py`

Adds direct OpenAI provider support behind `LLMClient`.

### `src/repopilot/llm/factory.py`

Adds provider selection based on `REPOPILOT_LLM_PROVIDER`.

### `src/repopilot/agent/preview.py`

Uses the provider factory when `use_llm=true` and falls back to deterministic
planning if the LLM returns invalid structured output.

### `src/repopilot/planning/llm_planner.py`

Strips Markdown fences before JSON parsing.

### `tests/test_openai_llm_client.py`

Tests OpenAI env loading, response parsing, provider errors, usage metadata, and
provider factory behavior with no real network calls.

## How To Explain This In An Interview

You can say:

"I added direct OpenAI support as a provider adapter behind the same LLMClient
interface used by OpenRouter. Provider choice is controlled by
REPOPILOT_LLM_PROVIDER, and OpenAI keys are read only from OPENAI_API_KEY. The
agent preview endpoint remains preview-only, and if an LLM returns invalid JSON,
the system falls back to deterministic planning instead of breaking the demo."
