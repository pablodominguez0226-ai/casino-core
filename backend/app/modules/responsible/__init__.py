"""Responsible Gaming & KYC module package.

Módulo educativo. Las verificaciones y límites son simulados y no reemplazan sistemas regulatorios reales.
"""
from app.modules.responsible.enums import DocumentType, KycStatus
from app.modules.responsible.exceptions import (
    DailyBetLimitExceededException,
    InvalidKycTransitionException,
    KycProfileNotFoundException,
    PlayerSelfExcludedException,
    ResponsibleGamingException,
    SessionDurationExceededException,
)
from app.modules.responsible.models import KycProfile, PlayerLimit, SelfExclusion
from app.modules.responsible.router import router
from app.modules.responsible.schemas import (
    KycProfileResponse,
    KycReviewRequest,
    KycSubmitRequest,
    PlayerLimitResponse,
    PlayerLimitUpdateRequest,
    SelfExclusionCreateRequest,
    SelfExclusionResponse,
    SelfExclusionStatusResponse,
)
from app.modules.responsible.services import ResponsibleGamingService

__all__ = [
    "DocumentType",
    "KycStatus",
    "ResponsibleGamingException",
    "PlayerSelfExcludedException",
    "DailyBetLimitExceededException",
    "SessionDurationExceededException",
    "KycProfileNotFoundException",
    "InvalidKycTransitionException",
    "PlayerLimit",
    "SelfExclusion",
    "KycProfile",
    "PlayerLimitUpdateRequest",
    "PlayerLimitResponse",
    "SelfExclusionCreateRequest",
    "SelfExclusionResponse",
    "SelfExclusionStatusResponse",
    "KycSubmitRequest",
    "KycReviewRequest",
    "KycProfileResponse",
    "ResponsibleGamingService",
    "router",
]
