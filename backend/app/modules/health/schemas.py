from pydantic import BaseModel, ConfigDict


class HealthResponse(BaseModel):
    """Schema for basic liveness check endpoint."""

    model_config = ConfigDict(extra="forbid")

    status: str
    environment: str


class HealthReadyResponse(BaseModel):
    """Schema for readiness check endpoint verifying database connectivity."""

    model_config = ConfigDict(extra="forbid")

    status: str
    database: str
