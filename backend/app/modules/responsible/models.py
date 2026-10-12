"""Responsible Gaming & KYC ORM models.

Módulo educativo. Las verificaciones y límites son simulados y no reemplazan sistemas regulatorios reales.
"""
from datetime import datetime
from typing import TYPE_CHECKING
import uuid

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    String,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin, utc_now
from app.modules.responsible.enums import DocumentType, KycStatus

if TYPE_CHECKING:
    from app.modules.identity.models import User


class PlayerLimit(Base, TimestampMixin):
    """Player responsible gaming limits configuration.

    Módulo educativo. Las verificaciones y límites son simulados y no reemplazan sistemas regulatorios reales.
    """

    __tablename__ = "player_limits"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    daily_bet_limit: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )
    daily_loss_limit: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )
    session_duration_minutes: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])

    def __repr__(self) -> str:
        return f"<PlayerLimit user_id={self.user_id} daily_bet={self.daily_bet_limit}>"


class SelfExclusion(Base, TimestampMixin):
    """Irrevocable self-exclusion record blocking player gameplay.

    Módulo educativo. Las verificaciones y límites son simulados y no reemplazan sistemas regulatorios reales.
    """

    __tablename__ = "self_exclusions"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    starts_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    reason: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])

    def __repr__(self) -> str:
        return f"<SelfExclusion user_id={self.user_id} expires_at={self.expires_at} is_active={self.is_active}>"


class KycProfile(Base, TimestampMixin):
    """Simulated KYC identification record.

    Módulo educativo. Las verificaciones y límites son simulados y no reemplazan sistemas regulatorios reales.
    """

    __tablename__ = "kyc_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    document_type: Mapped[DocumentType] = mapped_column(
        SAEnum(DocumentType, name="document_type"),
        nullable=False,
    )
    document_number: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    status: Mapped[KycStatus] = mapped_column(
        SAEnum(KycStatus, name="kyc_status"),
        default=KycStatus.PENDING,
        index=True,
        nullable=False,
    )
    rejection_reason: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    reviewer: Mapped["User | None"] = relationship("User", foreign_keys=[reviewed_by])

    def __repr__(self) -> str:
        return f"<KycProfile user_id={self.user_id} status={self.status}>"
