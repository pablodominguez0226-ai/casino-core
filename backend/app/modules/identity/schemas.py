from datetime import date
from typing import Any
import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserRegisterRequest(BaseModel):
    """Payload for registering a new player under a specific operator."""

    email: EmailStr
    password: str = Field(..., min_length=8, description="User plaintext password (minimum 8 characters)")
    operator_slug: str = Field(..., min_length=1, max_length=50, description="Slug of the tenant operator")
    username: str = Field(..., min_length=3, max_length=50, description="Player unique gaming username")
    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    birth_date: date | None = None


class LoginRequest(BaseModel):
    """Payload for authenticating a user with credentials."""

    email: EmailStr
    password: str
    operator_slug: str = Field(..., min_length=1, max_length=50, description="Slug of the tenant operator")


class TokenResponse(BaseModel):
    """Response containing JWT access token and refresh token."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    """Payload for requesting access token renewal using a refresh token."""

    refresh_token: str


class UserResponse(BaseModel):
    """Public user response schema with assigned role names."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    operator_id: uuid.UUID
    email: str
    is_active: bool
    roles: list[str] = Field(default_factory=list)

    @field_validator("roles", mode="before")
    @classmethod
    def extract_role_names(cls, v: Any) -> list[str]:
        if isinstance(v, (list, set)):
            return [r.name if hasattr(r, "name") else str(r) for r in v]
        return v
