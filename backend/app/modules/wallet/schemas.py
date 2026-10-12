from datetime import datetime
import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.modules.wallet.enums import LedgerEntryType


class WalletResponse(BaseModel):
    """Schema representing user wallet state and balance."""

    id: uuid.UUID
    user_id: uuid.UUID
    balance: int
    currency: str
    is_locked: bool

    model_config = ConfigDict(from_attributes=True)


class LedgerEntryResponse(BaseModel):
    """Schema representing an immutable ledger transaction movement."""

    id: uuid.UUID
    wallet_id: uuid.UUID
    entry_type: LedgerEntryType
    amount: int
    balance_before: int
    balance_after: int
    idempotency_key: str | None = None
    created_at: datetime
    reference_id: uuid.UUID | None = None
    description: str | None = None

    model_config = ConfigDict(from_attributes=True)


class FaucetRequest(BaseModel):
    """Request schema for reloading virtual credits (max 100,000 per request)."""

    amount: int = Field(
        ...,
        gt=0,
        le=100000,
        description="Amount of virtual credits to load (minimum 1, maximum 100,000)",
    )


class TransactionRequest(BaseModel):
    """Request schema for executing a financial transaction on the wallet."""

    amount: int = Field(
        ...,
        gt=0,
        description="Amount of virtual credits for this transaction (must be positive)",
    )
    reference_id: uuid.UUID | None = Field(
        default=None,
        description="Optional external UUID reference (e.g. game round ID)",
    )
    description: str | None = Field(
        default=None,
        max_length=255,
        description="Optional human-readable description of the transaction",
    )


class WalletReconciliationResponse(BaseModel):
    """Response schema summarizing consistency audit between wallet and ledger."""

    wallet_id: uuid.UUID
    cached_balance: int
    calculated_ledger_balance: int
    is_consistent: bool
