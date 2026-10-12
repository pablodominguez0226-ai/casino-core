"""Responsible Gaming & KYC Pydantic schemas.

Módulo educativo. Las verificaciones y límites son simulados y no reemplazan sistemas regulatorios reales.
"""
from datetime import datetime
import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.modules.responsible.enums import DocumentType, KycStatus


class PlayerLimitUpdateRequest(BaseModel):
    """Payload to configure or update responsible gaming limits.

    Módulo educativo. Las verificaciones y límites son simulados y no reemplazan sistemas regulatorios reales.
    """

    daily_bet_limit: int | None = Field(
        default=None,
        ge=100,
        description="Daily maximum accumulated bet amount allowed in virtual credits.",
    )
    daily_loss_limit: int | None = Field(
        default=None,
        ge=0,
        description="Daily maximum net loss allowed in virtual credits.",
    )
    session_duration_minutes: int | None = Field(
        default=None,
        ge=10,
        description="Maximum continuous gameplay session duration in minutes.",
    )


class PlayerLimitResponse(BaseModel):
    """Responsible gaming limits configured for a player.

    Módulo educativo. Las verificaciones y límites son simulados y no reemplazan sistemas regulatorios reales.
    """

    user_id: uuid.UUID
    daily_bet_limit: int | None = None
    daily_loss_limit: int | None = None
    session_duration_minutes: int | None = None
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SelfExclusionCreateRequest(BaseModel):
    """Payload to request irrevocable player self-exclusion.

    Módulo educativo. Las verificaciones y límites son simulados y no reemplazan sistemas regulatorios reales.
    """

    duration_days: int = Field(
        ...,
        ge=1,
        le=3650,
        description="Irrevocable self-exclusion duration in calendar days (1 to 3650 days).",
    )
    reason: str | None = Field(
        default=None,
        max_length=255,
        description="Optional reason provided by the player.",
    )


class SelfExclusionResponse(BaseModel):
    """Self-exclusion record confirmation.

    Módulo educativo. Las verificaciones y límites son simulados y no reemplazan sistemas regulatorios reales.
    """

    id: uuid.UUID
    user_id: uuid.UUID
    starts_at: datetime
    expires_at: datetime
    is_active: bool
    reason: str | None = None

    model_config = ConfigDict(from_attributes=True)


class SelfExclusionStatusResponse(BaseModel):
    """Current self-exclusion status of the authenticated player.

    Módulo educativo. Las verificaciones y límites son simulados y no reemplazan sistemas regulatorios reales.
    """

    is_excluded: bool
    active_exclusion: SelfExclusionResponse | None = None

    model_config = ConfigDict(from_attributes=True)


class KycSubmitRequest(BaseModel):
    """Payload to submit simulated KYC identity verification.

    Módulo educativo. Las verificaciones y límites son simulados y no reemplazan sistemas regulatorios reales.
    """

    document_type: DocumentType = Field(
        ...,
        description="Type of identity document provided.",
    )
    document_number: str = Field(
        ...,
        min_length=4,
        max_length=50,
        description="Official document identification number.",
    )


class KycReviewRequest(BaseModel):
    """Payload for compliance officers to review and approve/reject simulated KYC.

    Módulo educativo. Las verificaciones y límites son simulados y no reemplazan sistemas regulatorios reales.
    """

    status: KycStatus = Field(
        ...,
        description="Updated KYC status: APPROVED or REJECTED.",
    )
    rejection_reason: str | None = Field(
        default=None,
        max_length=255,
        description="Mandatory or descriptive reason when rejecting KYC.",
    )


class KycProfileResponse(BaseModel):
    """Simulated KYC profile response.

    Módulo educativo. Las verificaciones y límites son simulados y no reemplazan sistemas regulatorios reales.
    """

    id: uuid.UUID
    user_id: uuid.UUID
    document_type: DocumentType
    document_number: str
    status: KycStatus
    rejection_reason: str | None = None
    submitted_at: datetime
    reviewed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
