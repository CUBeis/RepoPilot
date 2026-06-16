# 07 - LLM-Backed Planner

Milestone 8 adds an LLM-backed planner that uses the existing `LLMClient`
abstraction. It builds the planning prompt, sends an `LLMRequest` through the
provided client, expects JSON content back, and validates that JSON into an
`ImplementationPlan`.

This milestone still does not call a real external LLM provider.

## What An LLM-Backed Planner Is

An LLM-backed planner is a planning component that delegates plan generation to
an LLM client. Instead of hardcoding every plan step, it sends the issue and
retrieved repository context to a model and expects a structured plan in return.

In this milestone, the model is represented by `FakeLLMClient` in tests.

## Why It Depends On LLMClient

The planner depends on the provider-independent `LLMClient` protocol instead of
OpenAI, Anthropic, or another SDK.

That keeps the planning layer flexible:

- Tests can use `FakeLLMClient`.
- Future production code can use a real provider adapter.
- The planner does not need to know which provider generated the response.

## Why We Still Use FakeLLMClient

FakeLLMClient keeps tests deterministic and avoids network calls, API keys,
costs, rate limits, and provider-specific behavior.

This lets RepoPilot prove the integration shape before adding real model calls.

## Prompt To Response To Structured Plan

The flow is:

1. `build_planning_prompt()` formats the issue and retrieved chunks.
2. `create_llm_implementation_plan()` wraps that prompt in an `LLMRequest`.
3. The injected `LLMClient` returns an `LLMResponse`.
4. The response content is parsed as JSON.
5. Pydantic validates the JSON as an `ImplementationPlan`.

The final result is the same structured plan type used by the deterministic
planner.

## Why JSON Parsing And Validation Matter

LLM output is text. RepoPilot needs structured data before any future agent can
safely act on it.

JSON parsing checks that the response is machine-readable. Pydantic validation
checks that the shape matches the fields RepoPilot expects:

- Objective
- Relevant files
- Ordered steps
- Risks
- Assumptions
- Confidence

## What Can Go Wrong

LLM structured outputs can fail in several ways:

- The response is not JSON.
- Required fields are missing.
- A step has the wrong shape.
- Confidence is outside the valid range.
- Lists are returned as strings or another wrong type.

This milestone raises `LLMPlanningError` for invalid JSON and invalid plan
structure so failures are clear.

## Preparing For Real Provider Integration

Later, RepoPilot can add an OpenAI, Anthropic, or local model adapter that
implements `LLMClient`. The LLM-backed planner should not need to change much
because it already depends on the abstraction.

The adapter will handle provider-specific API calls while this planner continues
to handle prompt creation, JSON parsing, and plan validation.

## Why This Still Does Not Edit Files

The LLM-backed planner only creates a plan. It does not write files, run tests,
call shell tools, or self-correct.

That separation keeps planning reviewable before any higher-risk action happens.

## Files Involved

### `src/repopilot/planning/llm_planner.py`

Defines `create_llm_implementation_plan()` and `LLMPlanningError`.

What to learn:

- The function builds an LLM request from the existing planning prompt.
- It uses `LLMClient` instead of a concrete provider.
- It parses JSON and validates it with the existing plan models.

### `tests/test_llm_planner.py`

Tests the LLM-backed planner with `FakeLLMClient`.

What to learn:

- LLM integrations can be tested without real LLM calls.
- Tests verify request construction, prompt content, JSON parsing, validation
  errors, request settings, and determinism.

## Interview Explanation

You can explain this feature like this:

"I added an LLM-backed planner that uses a provider-independent LLM client
interface. It builds the existing planning prompt, sends it through an injected
client, expects JSON back, and validates that JSON into the same
ImplementationPlan model used by the deterministic planner. Tests use a fake
client, so the system proves the integration without real API calls or file
editing."
