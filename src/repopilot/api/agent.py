from fastapi import APIRouter, HTTPException

from repopilot.agent import AgentPreviewError, create_agent_preview
from repopilot.context import ContextBuildError
from repopilot.llm import (
    LLMProviderConfigurationError,
    OpenAIConfigurationError,
    OpenAIProviderError,
    OpenRouterConfigurationError,
    OpenRouterLLMError,
)
from repopilot.planning import LLMPlanningError, PlanningError
from repopilot.repository import RepositoryScanError
from repopilot.schemas.agent import AgentPreviewRequest, AgentPreviewResponse

router = APIRouter(tags=["agent"])


@router.post("/agent/preview", response_model=AgentPreviewResponse)
def preview_agent(request: AgentPreviewRequest) -> AgentPreviewResponse:
    """Return a safe agent preview without mutating files or running commands."""
    try:
        return create_agent_preview(
            root_path=request.root_path,
            issue=request.issue,
            top_k=request.top_k,
            max_preview_chars=request.max_preview_chars,
            use_llm=request.use_llm,
        )
    except (
        LLMProviderConfigurationError,
        OpenAIConfigurationError,
        OpenRouterConfigurationError,
    ) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except (OpenAIProviderError, OpenRouterLLMError, LLMPlanningError) as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    except (
        AgentPreviewError,
        ContextBuildError,
        PlanningError,
        RepositoryScanError,
    ) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
