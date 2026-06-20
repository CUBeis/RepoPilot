from __future__ import annotations

import json

from pydantic import ValidationError

from repopilot.context.models import RepositoryContext
from repopilot.llm.client import LLMClient
from repopilot.llm.models import LLMMessage, LLMRequest
from repopilot.planning.models import ImplementationPlan
from repopilot.planning.prompt import PlanningPromptError, build_planning_prompt

DEFAULT_LLM_PLANNER_MODEL = "fake-planner"


class LLMPlanningError(ValueError):
    """Raised when an LLM-backed implementation plan cannot be created."""


def create_llm_implementation_plan(
    issue: str,
    context: RepositoryContext,
    llm_client: LLMClient,
    *,
    model: str = DEFAULT_LLM_PLANNER_MODEL,
    temperature: float = 0.0,
    max_tokens: int | None = None,
) -> ImplementationPlan:
    """Create an implementation plan from JSON returned by an LLM client."""
    request = _build_llm_request(
        issue=issue,
        context=context,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    response = llm_client.generate(request)
    plan_data = _parse_response_json(response.content)
    return _validate_plan(plan_data)


def _build_llm_request(
    *,
    issue: str,
    context: RepositoryContext,
    model: str,
    temperature: float,
    max_tokens: int | None,
) -> LLMRequest:
    try:
        prompt = build_planning_prompt(issue, context)
    except PlanningPromptError as error:
        raise LLMPlanningError(str(error)) from error

    try:
        return LLMRequest(
            messages=[
                LLMMessage(
                    role="system",
                    content=(
                        "You are RepoPilot's planning engine. Return only JSON "
                        "that matches the ImplementationPlan schema."
                    ),
                ),
                LLMMessage(role="user", content=prompt),
            ],
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    except ValidationError as error:
        raise LLMPlanningError(f"Invalid LLM request settings: {error}") from error


def _parse_response_json(content: str) -> object:
    candidates = [content.strip()]
    stripped_fence_content = _strip_markdown_fence(content)
    if stripped_fence_content not in candidates:
        candidates.append(stripped_fence_content)

    for candidate in candidates:
        if not candidate:
            continue
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue

    raise LLMPlanningError("LLM response content was not valid JSON")


def _strip_markdown_fence(content: str) -> str:
    lines = content.strip().splitlines()
    if len(lines) < 2:
        return content.strip()

    first_line = lines[0].strip()
    last_line = lines[-1].strip()
    if first_line.startswith("```") and last_line == "```":
        return "\n".join(lines[1:-1]).strip()

    return content.strip()



def _validate_plan(plan_data: object) -> ImplementationPlan:
    try:
        return ImplementationPlan.model_validate(plan_data)
    except ValidationError as error:
        raise LLMPlanningError(
            "LLM response JSON did not match the ImplementationPlan schema"
        ) from error
