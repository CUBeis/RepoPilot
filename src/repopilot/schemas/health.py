from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Response payload for the health endpoint."""

    status: str
    service: str
    version: str
