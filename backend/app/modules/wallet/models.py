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
    Integer,
    String,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin, utc_now
from app.modules.wallet.enums import LedgerEntryType

if TYPE_CHECKING:
    from app.modules.identity.models import User
    from app.modules.operators.models import Operator


class Wallet(Base, TimestampMixin):
    """Wallet entity representing a user's virtual credit balance under an operator."""

    __tablename__ = "wallets"

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
    operator_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("operators.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    balance: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
        nullable=False,
    )
    currency: Mapped[str] = mapped_column(
        String(10),
        default="CREDITS",
        nullable=False,
    )
    is_locked: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Relationships
    entries: Mapped[list["LedgerEntry"]] = relationship(
        "LedgerEntry",
        back_populates="wallet",
        cascade="all, delete-orphan",
        order_by="LedgerEntry.created_at.asc()",
    )
    user: Mapped["User"] = relationship("User")
    operator: Mapped["Operator"] = relationship("Operator")

    __table_args__ = (
        CheckConstraint("balance >= 0", name="chk_wallet_balance_non_negative"),
    )

    def __repr__(self) -> str:
        return f"<Wallet(id={self.id}, user_id={self.user_id}, balance={self.balance}, is_locked={self.is_locked})>"


class LedgerEntry(Base):
    """Immutable, append-only ledger entry recording all wallet financial movements."""

    __tablename__ = "ledger_entries"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    wallet_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("wallets.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    entry_type: Mapped[LedgerEntryType] = mapped_column(
        SAEnum(LedgerEntryType, name="ledger_entry_type"),
        nullable=False,
    )
    amount: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )
    balance_before: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )
    balance_after: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )
    idempotency_key: Mapped[str | None] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=True,
    )
    reference_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        index=True,
        nullable=True,
    )
    description: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    # Relationships
    wallet: Mapped["Wallet"] = relationship("Wallet", back_populates="entries")

    __table_args__ = (
        CheckConstraint("amount > 0", name="chk_ledger_amount_positive"),
    )

    def __repr__(self) -> str:
        return (
            f"<LedgerEntry(id={self.id}, wallet_id={self.wallet_id}, "
            f"type={self.entry_type}, amount={self.amount}, "
            f"before={self.balance_before}, after={self.balance_after})>"
        )


class IdempotencyRecord(Base):
    """Persistent idempotency store guaranteeing exactly-once semantics for financial mutations."""

    __tablename__ = "idempotency_records"

    key: Mapped[str] = mapped_column(
        String(100),
        primary_key=True,
        nullable=False,
    )
    wallet_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("wallets.id", ondelete="CASCADE"),
        nullable=False,
    )
    response_status: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    response_payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    # Relationships
    wallet: Mapped["Wallet"] = relationship("Wallet")

    def __repr__(self) -> str:
        return f"<IdempotencyRecord(key='{self.key}', wallet_id={self.wallet_id}, status={self.response_status})>"
