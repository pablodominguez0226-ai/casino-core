"""Responsible Gaming & KYC domain service.

Módulo educativo. Las verificaciones y límites son simulados y no reemplazan sistemas regulatorios reales.
"""
from datetime import timedelta
import logging
import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import utc_now
from app.modules.audit.services import AuditService
from app.modules.gaming.enums import GameSessionStatus
from app.modules.gaming.models import GameRound, GameSession
from app.modules.identity.models import Role, User
from app.modules.responsible.enums import KycStatus
from app.modules.responsible.exceptions import (
    DailyBetLimitExceededException,
    InvalidKycTransitionException,
    KycProfileNotFoundException,
    PlayerSelfExcludedException,
    SessionDurationExceededException,
)
from app.modules.responsible.models import KycProfile, PlayerLimit, SelfExclusion
from app.modules.responsible.schemas import (
    KycReviewRequest,
    KycSubmitRequest,
    PlayerLimitUpdateRequest,
)

logger = logging.getLogger(__name__)


class ResponsibleGamingService:
    """Domain service managing player limits, self-exclusions, and simulated KYC.

    Módulo educativo. Las verificaciones y límites son simulados y no reemplazan sistemas regulatorios reales.
    """

    @classmethod
    async def get_or_create_limits(
        cls,
        db: AsyncSession,
        user_id: uuid.UUID,
    ) -> PlayerLimit:
        """Retrieve existing player responsible gaming limits or initialize empty configuration."""
        stmt = select(PlayerLimit).where(PlayerLimit.user_id == user_id)
        limits = await db.scalar(stmt)
        if not limits:
            limits = PlayerLimit(
                id=uuid.uuid4(),
                user_id=user_id,
                daily_bet_limit=None,
                daily_loss_limit=None,
                session_duration_minutes=None,
            )
            db.add(limits)
            await db.commit()
            await db.refresh(limits)
        return limits

    @classmethod
    async def update_limits(
        cls,
        db: AsyncSession,
        user_id: uuid.UUID,
        data: PlayerLimitUpdateRequest,
    ) -> PlayerLimit:
        """Update player limits and record an immutable forensic audit event."""
        limits = await cls.get_or_create_limits(db, user_id)

        update_dict = data.model_dump(exclude_unset=True)
        if "daily_bet_limit" in update_dict:
            limits.daily_bet_limit = update_dict["daily_bet_limit"]
        if "daily_loss_limit" in update_dict:
            limits.daily_loss_limit = update_dict["daily_loss_limit"]
        if "session_duration_minutes" in update_dict:
            limits.session_duration_minutes = update_dict["session_duration_minutes"]

        limits.updated_at = utc_now()

        await AuditService.log_event(
            db=db,
            action="PLAYER_LIMITS_UPDATED",
            resource_type="PLAYER_LIMITS",
            resource_id=limits.id,
            user_id=user_id,
            details={
                "daily_bet_limit": limits.daily_bet_limit,
                "daily_loss_limit": limits.daily_loss_limit,
                "session_duration_minutes": limits.session_duration_minutes,
            },
        )

        await db.commit()
        await db.refresh(limits)
        return limits

    @classmethod
    async def apply_self_exclusion(
        cls,
        db: AsyncSession,
        user_id: uuid.UUID,
        days: int,
        reason: str | None = None,
    ) -> SelfExclusion:
        """Apply an irrevocable self-exclusion, cancel active game sessions, and emit audit log."""
        starts_at = utc_now()
        expires_at = starts_at + timedelta(days=days)

        exclusion = SelfExclusion(
            id=uuid.uuid4(),
            user_id=user_id,
            starts_at=starts_at,
            expires_at=expires_at,
            reason=reason,
            is_active=True,
        )
        db.add(exclusion)

        # Invalidate / cancel all active game sessions for this player immediately
        stmt_cancel = (
            update(GameSession)
            .where(
                GameSession.user_id == user_id,
                GameSession.status == GameSessionStatus.ACTIVE,
            )
            .values(
                status=GameSessionStatus.CANCELLED,
                ended_at=utc_now(),
                updated_at=utc_now(),
            )
        )
        await db.execute(stmt_cancel)

        await AuditService.log_event(
            db=db,
            action="SELF_EXCLUSION_APPLIED",
            resource_type="SELF_EXCLUSION",
            resource_id=exclusion.id,
            user_id=user_id,
            details={
                "duration_days": days,
                "starts_at": starts_at.isoformat(),
                "expires_at": expires_at.isoformat(),
                "reason": reason,
            },
        )

        await db.commit()
        await db.refresh(exclusion)
        return exclusion

    @classmethod
    async def get_active_self_exclusion(
        cls,
        db: AsyncSession,
        user_id: uuid.UUID,
    ) -> SelfExclusion | None:
        """Return the current active self-exclusion for the player if one exists and is not expired."""
        stmt = (
            select(SelfExclusion)
            .where(
                SelfExclusion.user_id == user_id,
                SelfExclusion.is_active.is_(True),
                SelfExclusion.expires_at > utc_now(),
            )
            .order_by(SelfExclusion.expires_at.desc())
            .limit(1)
        )
        return await db.scalar(stmt)

    @classmethod
    async def validate_player_can_play(
        cls,
        db: AsyncSession,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        bet_amount: int,
    ) -> None:
        """Enforce responsible gaming invariants before a spin or round is executed.

        Safeguards:
        1. Invariant: Player cannot have active self-exclusion (HTTP 403).
        2. Daily Bet Limit: Sum of rounds in last 24h + bet_amount must not exceed daily_bet_limit (HTTP 409).
        3. Session Duration: Elapsed session time must not exceed session_duration_minutes (HTTP 409).
        """
        # 1. Check self-exclusion
        exclusion = await cls.get_active_self_exclusion(db, user_id)
        if exclusion:
            raise PlayerSelfExcludedException(
                message=f"Player is self-excluded until {exclusion.expires_at.isoformat()}. Gameplay prohibited.",
                expires_at=exclusion.expires_at,
            )

        # 2. Check player limits
        stmt_limits = select(PlayerLimit).where(PlayerLimit.user_id == user_id)
        limits = await db.scalar(stmt_limits)

        if limits:
            # 2a. Daily Bet Limit enforcement
            if limits.daily_bet_limit is not None:
                since = utc_now() - timedelta(hours=24)
                stmt_volume = (
                    select(func.coalesce(func.sum(GameRound.bet_amount), 0))
                    .join(GameSession, GameRound.session_id == GameSession.id)
                    .where(
                        GameSession.user_id == user_id,
                        GameRound.created_at >= since,
                    )
                )
                current_volume = int((await db.scalar(stmt_volume)) or 0)
                if current_volume + bet_amount > limits.daily_bet_limit:
                    raise DailyBetLimitExceededException(
                        message=(
                            f"Daily bet limit of {limits.daily_bet_limit} exceeded. "
                            f"Current 24h volume: {current_volume}, attempted bet: {bet_amount}."
                        ),
                        limit=limits.daily_bet_limit,
                        current=current_volume,
                        attempted=bet_amount,
                    )

            # 2b. Session Duration enforcement
            if limits.session_duration_minutes is not None:
                session = await db.get(GameSession, session_id)
                if session and session.started_at:
                    elapsed_seconds = (utc_now() - session.started_at).total_seconds()
                    if elapsed_seconds > limits.session_duration_minutes * 60:
                        elapsed_mins = int(elapsed_seconds / 60)
                        raise SessionDurationExceededException(
                            message=(
                                f"Session duration limit of {limits.session_duration_minutes} minutes exceeded. "
                                f"Current session duration: {elapsed_mins} minutes."
                            ),
                            max_duration_minutes=limits.session_duration_minutes,
                            elapsed_minutes=elapsed_mins,
                        )

    @classmethod
    async def submit_kyc(
        cls,
        db: AsyncSession,
        user_id: uuid.UUID,
        data: KycSubmitRequest,
    ) -> KycProfile:
        """Submit or resubmit simulated KYC identity verification."""
        stmt = select(KycProfile).where(KycProfile.user_id == user_id)
        profile = await db.scalar(stmt)

        if profile:
            if profile.status == KycStatus.APPROVED:
                raise InvalidKycTransitionException("KYC profile is already approved and verified.")
            profile.document_type = data.document_type
            profile.document_number = data.document_number
            profile.status = KycStatus.PENDING
            profile.rejection_reason = None
            profile.reviewed_by = None
            profile.reviewed_at = None
            profile.submitted_at = utc_now()
            profile.updated_at = utc_now()
        else:
            profile = KycProfile(
                id=uuid.uuid4(),
                user_id=user_id,
                document_type=data.document_type,
                document_number=data.document_number,
                status=KycStatus.PENDING,
                submitted_at=utc_now(),
            )
            db.add(profile)

        await db.flush()

        await AuditService.log_event(
            db=db,
            action="KYC_SUBMITTED",
            resource_type="KYC_PROFILE",
            resource_id=profile.id,
            user_id=user_id,
            details={
                "document_type": profile.document_type.value,
                "document_number": profile.document_number,
            },
        )

        await db.commit()
        await db.refresh(profile)
        return profile

    @classmethod
    async def review_kyc(
        cls,
        db: AsyncSession,
        profile_id: uuid.UUID,
        reviewer_id: uuid.UUID,
        data: KycReviewRequest,
    ) -> KycProfile:
        """Review simulated KYC dossier. Only compliance officers or super administrators can review."""
        if data.status not in (KycStatus.APPROVED, KycStatus.REJECTED):
            raise InvalidKycTransitionException("Review status must be either APPROVED or REJECTED.")

        # Validate reviewer permissions
        stmt_reviewer = (
            select(User)
            .where(User.id == reviewer_id)
            .options(selectinload(User.roles).selectinload(Role.permissions))
        )
        reviewer = await db.scalar(stmt_reviewer)
        if not reviewer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reviewer user not found",
            )

        reviewer_perms = {p.code for r in reviewer.roles for p in r.permissions}
        reviewer_roles = {r.name for r in reviewer.roles}

        if (
            "compliance:write" not in reviewer_perms
            and "system:admin" not in reviewer_perms
            and "COMPLIANCE" not in reviewer_roles
            and "SUPER_ADMIN" not in reviewer_roles
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: Insufficient permissions for KYC review",
            )

        profile = await db.get(KycProfile, profile_id)
        if not profile:
            raise KycProfileNotFoundException(f"KYC profile '{profile_id}' not found.")

        profile.status = data.status
        profile.rejection_reason = data.rejection_reason if data.status == KycStatus.REJECTED else None
        profile.reviewed_by = reviewer_id
        profile.reviewed_at = utc_now()
        profile.updated_at = utc_now()

        await AuditService.log_event(
            db=db,
            action=f"KYC_{data.status.value}",
            resource_type="KYC_PROFILE",
            resource_id=profile.id,
            user_id=profile.user_id,
            details={
                "status": data.status.value,
                "rejection_reason": profile.rejection_reason,
                "reviewed_by": str(reviewer_id),
            },
        )

        await db.commit()
        await db.refresh(profile)
        return profile

    @classmethod
    async def get_kyc_profile(
        cls,
        db: AsyncSession,
        user_id: uuid.UUID,
    ) -> KycProfile | None:
        """Retrieve simulated KYC profile for a given user."""
        stmt = select(KycProfile).where(KycProfile.user_id == user_id)
        return await db.scalar(stmt)
