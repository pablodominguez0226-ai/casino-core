"""Gaming ORM models.

Simulación educativa. RNG no apto ni certificado para juego con dinero real.
"""
from datetime import datetime
from typing import TYPE_CHECKING, Any
import uuid

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    String,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin, utc_now
from app.modules.gaming.enums import GameSessionStatus, GameType

if TYPE_CHECKING:
    from app.modules.identity.models import User
    from app.modules.operators.models import Operator


class Game(Base, TimestampMixin):
    """Game catalog entity defining game rules, betting boundaries, and configurations."""

    __tablename__ = "games"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    operator_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("operators.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    code: Mapped[str] = mapped_column(
        String(50),
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    game_type: Mapped[GameType] = mapped_column(
        SAEnum(GameType, name="game_type"),
        default=GameType.SLOT,
        nullable=False,
    )
    min_bet: Mapped[int] = mapped_column(
        BigInteger,
        default=10,
        nullable=False,
    )
    max_bet: Mapped[int] = mapped_column(
        BigInteger,
        default=1000,
        nullable=False,
    )
    config: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        default=dict,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # Relationships
    operator: Mapped["Operator"] = relationship("Operator")
    sessions: Mapped[list["GameSession"]] = relationship(
        "GameSession",
        back_populates="game",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint("min_bet > 0", name="chk_game_min_bet_positive"),
        CheckConstraint("max_bet >= min_bet", name="chk_game_max_bet_ge_min"),
    )

    def __repr__(self) -> str:
        return f"<Game(id={self.id}, code='{self.code}', name='{self.name}', type={self.game_type})>"


class GameSession(Base, TimestampMixin):
    """Game session entity tracking player engagement lifecycle."""

    __tablename__ = "game_sessions"

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
    game_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("games.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    status: Mapped[GameSessionStatus] = mapped_column(
        SAEnum(GameSessionStatus, name="game_session_status"),
        default=GameSessionStatus.ACTIVE,
        nullable=False,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    user: Mapped["User"] = relationship("User")
    game: Mapped["Game"] = relationship("Game", back_populates="sessions")
    rounds: Mapped[list["GameRound"]] = relationship(
        "GameRound",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="GameRound.created_at.desc()",
    )

    def __repr__(self) -> str:
        return f"<GameSession(id={self.id}, user_id={self.user_id}, game_id={self.game_id}, status={self.status})>"


class GameRound(Base):
    """Immutable game round entity recording bet, RNG outcome, and payout."""

    __tablename__ = "game_rounds"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("game_sessions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    bet_amount: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )
    payout_amount: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
        nullable=False,
    )
    round_data: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    # Relationships
    session: Mapped["GameSession"] = relationship("GameSession", back_populates="rounds")

    __table_args__ = (
        CheckConstraint("bet_amount > 0", name="chk_game_round_bet_amount_positive"),
        CheckConstraint("payout_amount >= 0", name="chk_game_round_payout_amount_non_negative"),
    )

    def __repr__(self) -> str:
        return f"<GameRound(id={self.id}, session_id={self.session_id}, bet={self.bet_amount}, payout={self.payout_amount})>"
