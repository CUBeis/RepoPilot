from fastapi import APIRouter, HTTPException

from repopilot.context import ContextBuildError, build_repository_context
from repopilot.repository import RepositoryScanError
from repopilot.schemas.context import (
    ContextChunkPreview,
    ContextPreviewRequest,
    ContextPreviewResponse,
)

router = APIRouter(tags=["context"])


@router.post(
    "/repositories/context-preview",
    response_model=ContextPreviewResponse,
)
def preview_repository_context(
    request: ContextPreviewRequest,
) -> ContextPreviewResponse:
    """Return bounded retrieved chunk previews for a repository query."""

    try:
        context = build_repository_context(
            request.root_path,
            request.query,
            top_k=request.top_k,
        )
    except (ContextBuildError, RepositoryScanError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    return ContextPreviewResponse(
        root_name=context.root_name,
        scanned_file_count=context.scanned_file_count,
        skipped_file_count=context.skipped_file_count,
        total_chunks=context.total_chunks,
        retrieved_count=len(context.retrieved_chunks),
        chunks=[
            ContextChunkPreview(
                path=retrieved_chunk.chunk.path,
                language=retrieved_chunk.chunk.language,
                start_line=retrieved_chunk.chunk.start_line,
                end_line=retrieved_chunk.chunk.end_line,
                score=retrieved_chunk.score,
                matched_terms=retrieved_chunk.matched_terms,
                preview=_truncate_preview(
                    retrieved_chunk.chunk.text,
                    request.max_preview_chars,
                ),
            )
            for retrieved_chunk in context.retrieved_chunks
        ],
    )


def _truncate_preview(text: str, max_preview_chars: int) -> str:
    return text[:max_preview_chars]
