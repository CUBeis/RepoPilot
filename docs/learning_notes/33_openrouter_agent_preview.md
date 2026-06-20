# Learning Note 33: OpenRouter LLM Provider And Agent Preview API

## What Was Built

Milestone 36 adds the first real-provider LLM adapter and a safe preview
endpoint:

```text
POST /agent/preview
```

The endpoint can build repository context, create either a deterministic plan or
an OpenRouter-backed plan, and return a bounded patch proposal preview.

It does not apply patches, run commands, generate repairs, start
self-correction, or write files.

## Why OpenRouter Fits This Milestone

RepoPilot already had a provider-independent `LLMClient` protocol and fake
clients for tests. OpenRouter exposes an OpenAI-compatible chat completions API,
so it is a good first real-provider adapter.

The new `OpenRouterLLMClient` translates RepoPilot's internal `LLMRequest` into
OpenRouter chat messages and translates the response back into `LLMResponse`.
The planning layer still depends only on `LLMClient`, not on OpenRouter itself.

## Environment Variables

The client reads configuration from environment variables:

- `OPENROUTER_API_KEY` is required.
- `OPENROUTER_MODEL` is optional and defaults to `~openai/gpt-latest`.
- `OPENROUTER_HTTP_REFERER` is optional.
- `OPENROUTER_APP_TITLE` is optional.

Secrets are never hardcoded, printed, or returned in API error messages.

## How The Agent Preview Works

The preview flow is:

```text
repository path + issue
-> build_repository_context()
-> deterministic planner OR OpenRouter-backed planner
-> safe read-only file reads for relevant files
-> deterministic patch proposal preview
-> markdown safety summary
```

When `use_llm=false`, RepoPilot uses the deterministic planner. When
`use_llm=true`, RepoPilot creates an `OpenRouterLLMClient` from environment
variables and sends the existing planning prompt through the LLM-backed planner.

## Why This Is Still Safe

The endpoint is preview-only. It can read repository files through existing safe
scanner/chunker/read-only layers, but it cannot mutate files.

It also does not:

- call patch application tools
- run validation commands
- generate repair proposals
- start self-correction loops
- expose full unbounded file content

Patch proposal content is returned only through bounded previews.

## Why Tests Still Mock Provider Calls

Tests inject fake HTTP clients for `OpenRouterLLMClient` and fake LLM clients for
the agent preview endpoint. That proves request construction, parsing, error
handling, and API behavior without relying on network access, API keys, rate
limits, or provider uptime.

This keeps the test suite deterministic even though the app now has a real
provider adapter.

## Files Added Or Updated

### `src/repopilot/llm/openrouter_client.py`

Implements `OpenRouterLLMClient`, configuration errors, provider errors, request
translation, response parsing, token usage mapping, and environment loading.

### `src/repopilot/agent/preview.py`

Composes context building, deterministic or LLM-backed planning, safe file reads,
patch proposal preview creation, and Markdown summary generation.

### `src/repopilot/api/agent.py`

Exposes `POST /agent/preview` and maps missing configuration, provider failures,
context errors, and planning errors into clear HTTP responses.

### `src/repopilot/schemas/agent.py`

Defines request and response schemas for the preview endpoint.

### `tests/test_openrouter_llm_client.py`

Tests OpenRouter environment configuration, request payloads, headers, response
parsing, usage metadata, invalid responses, and error wrapping.

### `tests/test_agent_preview_api.py`

Tests deterministic preview mode, mocked LLM preview mode, missing API key,
provider errors, bounded previews, no hidden side effects, and deterministic
responses.

## How To Explain This In An Interview

You can say:

"I added RepoPilot's first real LLM provider adapter using OpenRouter, but kept
the architecture safe. The adapter implements the existing provider-independent
LLMClient protocol, so planning does not depend on a vendor SDK. Then I exposed a
preview-only API that can build context, call the planner, and return a bounded
patch proposal preview. It never applies patches or runs commands, and tests mock
the provider path so the suite stays deterministic."
