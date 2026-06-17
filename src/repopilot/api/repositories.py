from fastapi import APIRouter, HTTPException

from repopilot.repository import RepositoryScanError, scan_repository
from repopilot.schemas.repositories import (
    RepositoryScanSummaryRequest,
    RepositoryScanSummaryResponse,
    ScannedFileSummary,
)

router = APIRouter(tags=["repositories"])


@router.post(
    "/repositories/scan-summary",
    response_model=RepositoryScanSummaryResponse,
)
def scan_repository_summary(
    request: RepositoryScanSummaryRequest,
) -> RepositoryScanSummaryResponse:
    """Return a safe read-only repository scan summary."""

    try:
        scan_result = scan_repository(request.root_path)
    except RepositoryScanError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    return RepositoryScanSummaryResponse(
        root_name=scan_result.root_name,
        file_count=scan_result.file_count,
        total_size_bytes=scan_result.total_size_bytes,
        skipped_count=scan_result.skipped_count,
        files=[
            ScannedFileSummary(
                path=scanned_file.path,
                language=scanned_file.language,
                extension=scanned_file.extension,
                size_bytes=scanned_file.size_bytes,
                line_count=scanned_file.line_count,
            )
            for scanned_file in scan_result.files
        ],
    )
