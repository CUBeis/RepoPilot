# 06 - LLM Client Abstraction

Milestone 7 adds a provider-independent LLM abstraction layer. It defines common
request and response models, a client protocol, and a deterministic fake client
for tests and future development.

This milestone does not call OpenAI, Anthropic, local models, or any external
LLM provider.

## Why We Need An LLM Client Abstraction

RepoPilot will eventually use LLMs for planning, reasoning, summaries, and
self-correction. If the rest of the codebase talks directly to one provider SDK,
the project becomes harder to test and harder to change.

An abstraction lets RepoPilot depend on a small internal contract instead of a
specific vendor.

## Why We Do Not Call A Real LLM Yet

Real LLM calls add API keys, network behavior, costs, rate limits, retries, and
provider-specific response formats.

This milestone intentionally avoids all of that. The goal is to define the
contract first, prove it with tests, and keep behavior deterministic.

## What Provider-Independent Means

Provider-independent means the request and response models are not tied to
OpenAI, Anthropic, or any local model runtime.

RepoPilot can use the same internal shapes for all providers:

- `LLMMessage`
- `LLMRequest`
- `LLMUsage`
- `LLMResponse`
- `LLMClient`

Later, provider-specific adapters can translate these models into the SDK calls
for each vendor.

## What The Models Do

`LLMMessage` stores a role and content.

`LLMRequest` stores messages, model name, temperature, and optional max tokens.
Temperature is validated so invalid values fail early.

`LLMUsage` stores optional token usage metadata.

`LLMResponse` stores generated content, model name, and optional usage.

## Why FakeLLMClient Is Useful

`FakeLLMClient` returns the same fixed response for every request. It also stores
the last request so tests can inspect what would have been sent to an LLM.

This is useful because:

- Tests stay deterministic.
- No API key is needed.
- No network call happens.
- Future planner code can be tested before real providers exist.

The fake client can also estimate stable token usage using simple word counts.
This is not real tokenizer behavior, but it is enough for tests and metadata
plumbing.

## How This Connects To Planning Later

The current planning layer is deterministic. A future milestone can add an
LLM-backed planner that:

1. Builds the planning prompt.
2. Sends an `LLMRequest` through an `LLMClient`.
3. Parses the `LLMResponse`.
4. Produces an `ImplementationPlan`.

Because the planner would depend on `LLMClient`, tests can use `FakeLLMClient`
while production code can use a real provider adapter later.

## Preparing For OpenAI, Anthropic, And Local Models

The abstraction keeps provider details at the edges. Later adapters can map:

- `LLMRequest.messages` to provider chat messages
- `LLMRequest.model` to provider model identifiers
- Provider output text to `LLMResponse.content`
- Provider token counts to `LLMUsage`

That gives RepoPilot flexibility without changing higher-level planning code.

## Files Involved

### `src/repopilot/llm/__init__.py`

Exports the public LLM abstraction API.

What to learn:

- A small package surface makes future provider adapters easier to add.

### `src/repopilot/llm/models.py`

Defines provider-independent Pydantic request and response models.

What to learn:

- Internal models give the rest of the app a stable contract.
- Validation catches invalid generation settings early.

### `src/repopilot/llm/client.py`

Defines the `LLMClient` protocol.

What to learn:

- Protocols let different clients share the same interface without inheritance.
- A real OpenAI client and fake test client can both implement `generate()`.

### `src/repopilot/llm/fake.py`

Defines `FakeLLMClient`.

What to learn:

- Fake clients make agentic systems testable before real integrations exist.
- Storing `last_request` helps tests verify prompts and settings.

### `tests/test_llm_client.py`

Tests the models, fake client, deterministic behavior, request tracking, token
usage, and validation.

What to learn:

- LLM-facing code can be tested without external APIs.
- Deterministic fakes are essential for reliable agent tests.

## Interview Explanation

You can explain this feature like this:

"I added a provider-independent LLM client abstraction before integrating any
real model. It defines typed request and response models, a protocol for clients,
and a deterministic fake client for tests. This lets RepoPilot's future planning
and agent layers depend on a stable internal contract instead of vendor SDKs,
while keeping tests fast, deterministic, and free from API keys."
