from datetime import datetime
from typing import Any
import uuid

from pydantic import BaseModel, ConfigDict, Field, model_validator


class OperatorCreateRequest(BaseModel):
    """Schema for tenant operator creation request."""

    name: str = Field(..., min_length=2, max_length=100, description="Legal or display name of the operator")
    slug: str = Field(..., min_length=2, max_length=50, description="Unique URL/tenant slug identifier")
    settings: dict[str, Any] | None = Field(default=None, description="Optional tenant-level configuration parameters")


class OperatorResponse(BaseModel):
    """Schema for tenant operator representation."""

    id: uuid.UUID
    name: str
    slug: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OperatorGameConfigUpdateRequest(BaseModel):
    """Schema for updating operator-specific game limits and activation status."""

    is_enabled: bool = Field(default=True, description="Whether this game is active for this tenant")
    min_bet: int = Field(..., gt=0, description="Minimum allowed wager in credits")
    max_bet: int = Field(..., gt=0, description="Maximum allowed wager in credits")
    custom_config: dict[str, Any] | None = Field(default=None, description="Optional game customization parameters")

    @model_validator(mode="after")
    def validate_bet_limits(self) -> "OperatorGameConfigUpdateRequest":
        if self.max_bet < self.min_bet:
            raise ValueError("max_bet must be greater than or equal to min_bet")
        return self


class OperatorGameConfigResponse(BaseModel):
    """Schema for operator game configuration response."""

    id: uuid.UUID
    operator_id: uuid.UUID
    game_id: uuid.UUID
    is_enabled: bool
    min_bet: int
    max_bet: int
    custom_config: dict[str, Any] | None = None

    model_config = ConfigDict(from_attributes=True)


class OperatorCatalogItemResponse(BaseModel):
    """Schema for an item in the operator's active game catalog."""

    id: uuid.UUID
    code: str
    name: str
    game_type: str
    is_enabled: bool
    min_bet: int
    max_bet: int
    custom_config: dict[str, Any] | None = None
