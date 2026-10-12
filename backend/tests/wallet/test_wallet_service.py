import uuid

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.models import User
from app.modules.operators.models import Operator
from app.modules.wallet.enums import LedgerEntryType
from app.modules.wallet.exceptions import (
    InsufficientFundsException,
    WalletLockedException,
    WalletNotFoundException,
)
from app.modules.wallet.models import LedgerEntry, Wallet
from app.modules.wallet.services import WalletService


@pytest.mark.asyncio
async def test_get_or_create_wallet(
    db_session: AsyncSession, test_user: User, test_operator: Operator
) -> None:
    """Validate get_or_create_wallet creates a wallet if not present and retrieves it on subsequent calls."""
    # First call: creates the wallet
    wallet = await WalletService.get_or_create_wallet(
        db_session, test_user.id, test_operator.id
    )
    assert wallet.id is not None
    assert wallet.user_id == test_user.id
    assert wallet.operator_id == test_operator.id
    assert wallet.balance == 0
    assert wallet.currency == "CREDITS"
    assert wallet.is_locked is False

    # Second call: returns existing wallet
    wallet_again = await WalletService.get_or_create_wallet(
        db_session, test_user.id, test_operator.id
    )
    assert wallet_again.id == wallet.id


@pytest.mark.asyncio
async def test_faucet_credit_and_balance_calculation(
    db_session: AsyncSession, test_wallet: Wallet
) -> None:
    """Validate faucet reload increments balance and records accurate balance_before and balance_after."""
    assert test_wallet.balance == 0

    entry = await WalletService.execute_transaction(
        db=db_session,
        wallet_id=test_wallet.id,
        amount=500,
        entry_type=LedgerEntryType.CREDIT,
        description="First faucet refill",
    )

    assert entry.amount == 500
    assert entry.balance_before == 0
    assert entry.balance_after == 500
    assert entry.entry_type == LedgerEntryType.CREDIT

    # Refresh wallet and verify persistence
    await db_session.refresh(test_wallet)
    assert test_wallet.balance == 500

    # Second credit
    entry2 = await WalletService.execute_transaction(
        db=db_session,
        wallet_id=test_wallet.id,
        amount=250,
        entry_type=LedgerEntryType.CREDIT,
        description="Second faucet refill",
    )
    assert entry2.balance_before == 500
    assert entry2.balance_after == 750

    await db_session.refresh(test_wallet)
    assert test_wallet.balance == 750


@pytest.mark.asyncio
async def test_debit_successful_and_ledger_entry(
    db_session: AsyncSession, test_wallet: Wallet
) -> None:
    """Validate debit correctly deducts balance and creates an immutable ledger entry."""
    # Seed initial balance
    await WalletService.execute_transaction(
        db=db_session,
        wallet_id=test_wallet.id,
        amount=1000,
        entry_type=LedgerEntryType.CREDIT,
    )

    # Debit 400
    ref_id = uuid.uuid4()
    entry = await WalletService.execute_transaction(
        db=db_session,
        wallet_id=test_wallet.id,
        amount=400,
        entry_type=LedgerEntryType.DEBIT,
        reference_id=ref_id,
        description="Bet placement",
    )

    assert entry.amount == 400
    assert entry.balance_before == 1000
    assert entry.balance_after == 600
    assert entry.entry_type == LedgerEntryType.DEBIT
    assert entry.reference_id == ref_id

    await db_session.refresh(test_wallet)
    assert test_wallet.balance == 600

    # Confirm ledger entry exists in database
    stmt = select(LedgerEntry).where(LedgerEntry.id == entry.id)
    saved_entry = await db_session.scalar(stmt)
    assert saved_entry is not None
    assert saved_entry.balance_after == 600


@pytest.mark.asyncio
async def test_debit_insufficient_funds_rejected_without_altering_balance(
    db_session: AsyncSession, test_wallet: Wallet
) -> None:
    """Validate that debit exceeding wallet balance raises InsufficientFundsException and preserves balance."""
    # Seed wallet with 300 credits
    await WalletService.execute_transaction(
        db=db_session,
        wallet_id=test_wallet.id,
        amount=300,
        entry_type=LedgerEntryType.CREDIT,
    )
    await db_session.refresh(test_wallet)
    assert test_wallet.balance == 300

    # Attempt to debit 500 credits
    with pytest.raises(InsufficientFundsException) as exc_info:
        await WalletService.execute_transaction(
            db=db_session,
            wallet_id=test_wallet.id,
            amount=500,
            entry_type=LedgerEntryType.DEBIT,
        )

    assert exc_info.value.status_code == 409
    assert "Insufficient funds" in exc_info.value.message

    # Balance must remain exactly 300
    await db_session.refresh(test_wallet)
    assert test_wallet.balance == 300

    # No new debit entry should exist
    stmt = (
        select(LedgerEntry)
        .where(LedgerEntry.wallet_id == test_wallet.id)
        .where(LedgerEntry.entry_type == LedgerEntryType.DEBIT)
    )
    debit_entries = (await db_session.scalars(stmt)).all()
    assert len(debit_entries) == 0


@pytest.mark.asyncio
async def test_wallet_locked_rejects_transactions(
    db_session: AsyncSession, test_wallet: Wallet
) -> None:
    """Validate that attempting a transaction on a locked wallet raises WalletLockedException."""
    test_wallet.is_locked = True
    await db_session.commit()
    await db_session.refresh(test_wallet)

    with pytest.raises(WalletLockedException) as exc_info:
        await WalletService.execute_transaction(
            db=db_session,
            wallet_id=test_wallet.id,
            amount=100,
            entry_type=LedgerEntryType.CREDIT,
        )

    assert exc_info.value.status_code == 423
    assert "locked" in exc_info.value.message


@pytest.mark.asyncio
async def test_wallet_not_found_raises_exception(db_session: AsyncSession) -> None:
    """Validate that operating on a non-existent wallet ID raises WalletNotFoundException."""
    fake_wallet_id = uuid.uuid4()
    with pytest.raises(WalletNotFoundException) as exc_info:
        await WalletService.execute_transaction(
            db=db_session,
            wallet_id=fake_wallet_id,
            amount=100,
            entry_type=LedgerEntryType.CREDIT,
        )
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_wallet_reconciliation_mathematical_consistency(
    db_session: AsyncSession, test_wallet: Wallet
) -> None:
    """Validate that reconciliation verifies wallet balance against the sum of ledger entries."""
    # Perform a sequence of operations
    # 1. Credit 1000
    await WalletService.execute_transaction(
        db=db_session,
        wallet_id=test_wallet.id,
        amount=1000,
        entry_type=LedgerEntryType.CREDIT,
    )
    # 2. Debit (bet simulation) 300
    await WalletService.execute_transaction(
        db=db_session,
        wallet_id=test_wallet.id,
        amount=300,
        entry_type=LedgerEntryType.BET_SIMULATION,
    )
    # 3. Credit (win simulation) 450
    await WalletService.execute_transaction(
        db=db_session,
        wallet_id=test_wallet.id,
        amount=450,
        entry_type=LedgerEntryType.WIN_SIMULATION,
    )
    # 4. Bonus credit 100
    await WalletService.execute_transaction(
        db=db_session,
        wallet_id=test_wallet.id,
        amount=100,
        entry_type=LedgerEntryType.BONUS,
    )
    # 5. Debit 150
    await WalletService.execute_transaction(
        db=db_session,
        wallet_id=test_wallet.id,
        amount=150,
        entry_type=LedgerEntryType.DEBIT,
    )

    # Expected balance: 1000 - 300 + 450 + 100 - 150 = 1100
    await db_session.refresh(test_wallet)
    assert test_wallet.balance == 1100

    reconciliation = await WalletService.reconcile_wallet(db_session, test_wallet.id)
    assert reconciliation.wallet_id == test_wallet.id
    assert reconciliation.cached_balance == 1100
    assert reconciliation.calculated_ledger_balance == 1100
    assert reconciliation.is_consistent is True


@pytest.mark.asyncio
async def test_database_check_constraints(
    db_session: AsyncSession, test_wallet: Wallet
) -> None:
    """Validate DB CheckConstraints: chk_wallet_balance_non_negative and chk_ledger_amount_positive."""
    # Test chk_ledger_amount_positive: amount must be > 0
    invalid_entry = LedgerEntry(
        wallet_id=test_wallet.id,
        entry_type=LedgerEntryType.CREDIT,
        amount=0,  # Violates amount > 0
        balance_before=0,
        balance_after=0,
    )
    db_session.add(invalid_entry)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()

    # Test chk_wallet_balance_non_negative: balance must be >= 0
    test_wallet.balance = -100  # Violates balance >= 0
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


# ==============================================================================
# API HTTP Endpoints Integration Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_api_get_wallet(
    client: httpx.AsyncClient, auth_headers: dict[str, str], test_user: User
) -> None:
    """Validate GET /api/v1/wallet returns the current user wallet information."""
    response = await client.get("/api/v1/wallet", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == str(test_user.id)
    assert data["balance"] == 0
    assert data["currency"] == "CREDITS"
    assert data["is_locked"] is False


@pytest.mark.asyncio
async def test_api_faucet_reload(
    client: httpx.AsyncClient, auth_headers: dict[str, str]
) -> None:
    """Validate POST /api/v1/wallet/faucet loads credits and requires Idempotency-Key header."""
    # Missing Idempotency-Key returns 422
    no_key_res = await client.post(
        "/api/v1/wallet/faucet",
        json={"amount": 5000},
        headers=auth_headers,
    )
    assert no_key_res.status_code == 422

    # Exceeding max limit (100000) returns 422
    over_limit_res = await client.post(
        "/api/v1/wallet/faucet",
        json={"amount": 100001},
        headers={**auth_headers, "Idempotency-Key": str(uuid.uuid4())},
    )
    assert over_limit_res.status_code == 422

    # Successful reload
    key = f"faucet-{uuid.uuid4()}"
    res = await client.post(
        "/api/v1/wallet/faucet",
        json={"amount": 5000},
        headers={**auth_headers, "Idempotency-Key": key},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["amount"] == 5000
    assert data["balance_before"] == 0
    assert data["balance_after"] == 5000
    assert data["idempotency_key"] == key

    # Check updated wallet balance
    wallet_res = await client.get("/api/v1/wallet", headers=auth_headers)
    assert wallet_res.json()["balance"] == 5000


@pytest.mark.asyncio
async def test_api_debit_and_ledger_history(
    client: httpx.AsyncClient, auth_headers: dict[str, str]
) -> None:
    """Validate debit endpoint and paginated GET /api/v1/wallet/ledger history."""
    # Refill 2000
    await client.post(
        "/api/v1/wallet/faucet",
        json={"amount": 2000},
        headers={**auth_headers, "Idempotency-Key": f"key-{uuid.uuid4()}"},
    )

    # Debit 700
    ref_id = str(uuid.uuid4())
    debit_res = await client.post(
        "/api/v1/wallet/debit",
        json={"amount": 700, "reference_id": ref_id, "description": "Spin 1"},
        headers={**auth_headers, "Idempotency-Key": f"debit-{uuid.uuid4()}"},
    )
    assert debit_res.status_code == 200
    assert debit_res.json()["balance_after"] == 1300

    # Get ledger entries
    ledger_res = await client.get("/api/v1/wallet/ledger?skip=0&limit=10", headers=auth_headers)
    assert ledger_res.status_code == 200
    entries = ledger_res.json()
    assert len(entries) == 2
    assert entries[0]["entry_type"] == "DEBIT"
    assert entries[0]["amount"] == 700
    assert entries[1]["entry_type"] == "CREDIT"
    assert entries[1]["amount"] == 2000


@pytest.mark.asyncio
async def test_api_reconcile_endpoint(
    client: httpx.AsyncClient, auth_headers: dict[str, str]
) -> None:
    """Validate GET /api/v1/wallet/reconcile self-audit endpoint."""
    await client.post(
        "/api/v1/wallet/faucet",
        json={"amount": 1000},
        headers={**auth_headers, "Idempotency-Key": f"reconcile-{uuid.uuid4()}"},
    )

    reconcile_res = await client.get("/api/v1/wallet/reconcile", headers=auth_headers)
    assert reconcile_res.status_code == 200
    data = reconcile_res.json()
    assert data["cached_balance"] == 1000
    assert data["calculated_ledger_balance"] == 1000
    assert data["is_consistent"] is True


@pytest.mark.asyncio
async def test_api_credit_endpoint(
    client: httpx.AsyncClient, auth_headers: dict[str, str]
) -> None:
    """Validate POST /api/v1/wallet/credit credits funds into wallet."""
    res = await client.post(
        "/api/v1/wallet/credit",
        json={"amount": 450, "description": "Manual prize credit"},
        headers=auth_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["entry_type"] == "CREDIT"
    assert data["amount"] == 450
    assert data["balance_after"] == 450

    # Test without trailing slash
    wallet_no_slash = await client.get("/api/v1/wallet", headers=auth_headers)
    assert wallet_no_slash.status_code == 200
    assert wallet_no_slash.json()["balance"] == 450


def test_wallet_models_representation(test_wallet: Wallet) -> None:
    """Validate string representations (__repr__) of wallet models."""
    from app.modules.wallet.models import IdempotencyRecord

    repr_wallet = repr(test_wallet)
    assert "<Wallet(" in repr_wallet
    assert "CREDITS" not in repr_wallet or "balance" in repr_wallet

    entry = LedgerEntry(
        wallet_id=test_wallet.id,
        entry_type=LedgerEntryType.CREDIT,
        amount=100,
        balance_before=0,
        balance_after=100,
    )
    repr_entry = repr(entry)
    assert "<LedgerEntry(" in repr_entry
    assert "amount=100" in repr_entry

    rec = IdempotencyRecord(
        key="test-key",
        wallet_id=test_wallet.id,
        response_status=200,
        response_payload={"ok": True},
    )
    repr_rec = repr(rec)
    assert "<IdempotencyRecord(" in repr_rec
    assert "key='test-key'" in repr_rec
