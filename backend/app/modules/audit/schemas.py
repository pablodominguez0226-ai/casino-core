"""Forensic Audit Pydantic Schemas."""
from datetime import datetime
from typing import Any
import uuid

from pydantic import BaseModel, ConfigDict, Field


class AuditLog(BaseModel):
    """Schema representing an immutable forensic audit event."""

    id: uuid.UUID
    user_id: uuid.UUID | None = None
    operator_id: uuid.UUID | None = None
    action: str
    resource_type: str
    resource_id: uuid.UUID | str | None = None
    details: dict[str, Any] | None = None
    ip_address: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedAuditLogs(BaseModel):
    """Schema representing paginated forensic audit records."""

    items: list[AuditLog]
    total: int
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)
