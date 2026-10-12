from typing import Any
import uuid

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    ForeignKey,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin


class Operator(Base, TimestampMixin):
    """Operator entity representing a B2B tenant or gaming platform operator."""

    __tablename__ = "operators"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    slug: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # Relationships
    game_configs: Mapped[list["OperatorGameConfig"]] = relationship(
        "OperatorGameConfig",
        back_populates="operator",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Operator(id={self.id}, slug='{self.slug}', is_active={self.is_active})>"


class OperatorGameConfig(Base, TimestampMixin):
    """Operator specific override for game catalog configuration and bet boundaries."""

    __tablename__ = "operator_game_configs"

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
    game_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("games.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    is_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    min_bet: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )
    max_bet: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )
    custom_config: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        default=dict,
    )

    # Relationships
    operator: Mapped["Operator"] = relationship("Operator", back_populates="game_configs")

    __table_args__ = (
        UniqueConstraint("operator_id", "game_id", name="uq_operator_game"),
        CheckConstraint("min_bet > 0", name="chk_operator_game_min_bet_positive"),
        CheckConstraint("max_bet >= min_bet", name="chk_operator_game_max_bet_ge_min"),
    )

    def __repr__(self) -> str:
        return (
            f"<OperatorGameConfig(operator_id={self.operator_id}, "
            f"game_id={self.game_id}, is_enabled={self.is_enabled}, "
            f"min_bet={self.min_bet}, max_bet={self.max_bet})>"
        )
