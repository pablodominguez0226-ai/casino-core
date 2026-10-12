"""Responsible Gaming & KYC API router.

Módulo educativo. Las verificaciones y límites son simulados y no reemplazan sistemas regulatorios reales.
"""
import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.modules.identity.dependencies import get_current_user, require_permission
from app.modules.identity.models import User
from app.modules.responsible.exceptions import KycProfileNotFoundException
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

router = APIRouter(prefix="/responsible", tags=["responsible-gaming"])


@router.get(
    "/limits",
    response_model=PlayerLimitResponse,
    summary="Get authenticated player limits",
)
@router.get(
    "/limits/",
    response_model=PlayerLimitResponse,
    include_in_schema=False,
)
async def get_player_limits(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> PlayerLimitResponse:
    """Retrieve responsible gaming limits for the authenticated player.

    Módulo educativo. Las verificaciones y límites son simulados y no reemplazan sistemas regulatorios reales.
    """
    limits = await ResponsibleGamingService.get_or_create_limits(
        db=db,
        user_id=current_user.id,
    )
    return PlayerLimitResponse.model_validate(limits)


@router.put(
    "/limits",
    response_model=PlayerLimitResponse,
    summary="Update authenticated player limits",
)
@router.put(
    "/limits/",
    response_model=PlayerLimitResponse,
    include_in_schema=False,
)
async def update_player_limits(
    data: PlayerLimitUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> PlayerLimitResponse:
    """Modify responsible gaming limits for the authenticated player.

    Módulo educativo. Las verificaciones y límites son simulados y no reemplazan sistemas regulatorios reales.
    """
    limits = await ResponsibleGamingService.update_limits(
        db=db,
        user_id=current_user.id,
        data=data,
    )
    return PlayerLimitResponse.model_validate(limits)


@router.post(
    "/self-exclusion",
    response_model=SelfExclusionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Request irrevocable player self-exclusion",
)
@router.post(
    "/self-exclusion/",
    response_model=SelfExclusionResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
async def request_self_exclusion(
    data: SelfExclusionCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> SelfExclusionResponse:
    """Request immediate and irrevocable self-exclusion.

    Módulo educativo. Las verificaciones y límites son simulados y no reemplazan sistemas regulatorios reales.
    """
    exclusion = await ResponsibleGamingService.apply_self_exclusion(
        db=db,
        user_id=current_user.id,
        days=data.duration_days,
        reason=data.reason,
    )
    return SelfExclusionResponse.model_validate(exclusion)


@router.get(
    "/self-exclusion/status",
    response_model=SelfExclusionStatusResponse,
    summary="Check active self-exclusion status",
)
@router.get(
    "/self-exclusion/status/",
    response_model=SelfExclusionStatusResponse,
    include_in_schema=False,
)
async def get_self_exclusion_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> SelfExclusionStatusResponse:
    """Check if the authenticated user has an active, non-expired self-exclusion.

    Módulo educativo. Las verificaciones y límites son simulados y no reemplazan sistemas regulatorios reales.
    """
    exclusion = await ResponsibleGamingService.get_active_self_exclusion(
        db=db,
        user_id=current_user.id,
    )
    return SelfExclusionStatusResponse(
        is_excluded=exclusion is not None,
        active_exclusion=SelfExclusionResponse.model_validate(exclusion) if exclusion else None,
    )


@router.post(
    "/kyc/submit",
    response_model=KycProfileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit simulated KYC identity verification",
)
@router.post(
    "/kyc/submit/",
    response_model=KycProfileResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
async def submit_kyc(
    data: KycSubmitRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> KycProfileResponse:
    """Submit simulated identity verification dossier.

    Módulo educativo. Las verificaciones y límites son simulados y no reemplazan sistemas regulatorios reales.
    """
    profile = await ResponsibleGamingService.submit_kyc(
        db=db,
        user_id=current_user.id,
        data=data,
    )
    return KycProfileResponse.model_validate(profile)


@router.get(
    "/kyc/status",
    response_model=KycProfileResponse,
    summary="Get user KYC status",
)
@router.get(
    "/kyc/status/",
    response_model=KycProfileResponse,
    include_in_schema=False,
)
async def get_kyc_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> KycProfileResponse:
    """Retrieve simulated KYC status for the authenticated user.

    Módulo educativo. Las verificaciones y límites son simulados y no reemplazan sistemas regulatorios reales.
    """
    profile = await ResponsibleGamingService.get_kyc_profile(
        db=db,
        user_id=current_user.id,
    )
    if not profile:
        raise KycProfileNotFoundException("KYC profile not found for user")
    return KycProfileResponse.model_validate(profile)


@router.post(
    "/admin/kyc/{profile_id}/review",
    response_model=KycProfileResponse,
    summary="Review and approve/reject KYC dossier (Compliance)",
)
@router.post(
    "/admin/kyc/{profile_id}/review/",
    response_model=KycProfileResponse,
    include_in_schema=False,
)
async def review_kyc(
    profile_id: uuid.UUID,
    data: KycReviewRequest,
    current_user: User = Depends(require_permission("compliance:write")),
    db: AsyncSession = Depends(get_db_session),
) -> KycProfileResponse:
    """Review and transition simulated KYC verification status.

    Módulo educativo. Las verificaciones y límites son simulados y no reemplazan sistemas regulatorios reales.
    """
    profile = await ResponsibleGamingService.review_kyc(
        db=db,
        profile_id=profile_id,
        reviewer_id=current_user.id,
        data=data,
    )
    return KycProfileResponse.model_validate(profile)
