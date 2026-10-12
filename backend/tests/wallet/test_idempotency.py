import uuid

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.wallet.enums import LedgerEntryType
from app.modules.wallet.exceptions import DuplicateTransactionException
from app.modules.wallet.models import IdempotencyRecord, LedgerEntry, Wallet
from app.modules.wallet.services import WalletService


@pytest.mark.asyncio
async def test_service_level_idempotency_same_payload(
    db_session: AsyncSession, test_wallet: Wallet
) -> None:
    """Validate that executing identical transactions with the same key returns the existing record without double deduction."""
    # Seed 1000 credits
    await WalletService.execute_transaction(
        db=db_session,
        wallet_id=test_wallet.id,
        amount=1000,
        entry_type=LedgerEntryType.CREDIT,
    )
    await db_session.refresh(test_wallet)
    assert test_wallet.balance == 1000

    idempotency_key = f"key-{uuid.uuid4()}"

    # First transaction: debit 300
    entry1 = await WalletService.execute_transaction(
        db=db_session,
        wallet_id=test_wallet.id,
        amount=300,
        entry_type=LedgerEntryType.DEBIT,
        idempotency_key=idempotency_key,
        description="First debit call",
    )
    assert entry1.amount == 300
    assert entry1.balance_before == 1000
    assert entry1.balance_after == 700

    await db_session.refresh(test_wallet)
    assert test_wallet.balance == 700

    # Second transaction with identical parameters and key
    entry2 = await WalletService.execute_transaction(
        db=db_session,
        wallet_id=test_wallet.id,
        amount=300,
        entry_type=LedgerEntryType.DEBIT,
        idempotency_key=idempotency_key,
        description="First debit call",
    )

    # Must return the same entry ID
    assert entry2.id == entry1.id
    assert entry2.balance_before == 1000
    assert entry2.balance_after == 700

    # Balance must NOT be deducted again
    await db_session.refresh(test_wallet)
    assert test_wallet.balance == 700

    # Only one ledger entry must exist for this idempotency key
    stmt_ledger = select(LedgerEntry).where(LedgerEntry.idempotency_key == idempotency_key)
    entries = (await db_session.scalars(stmt_ledger)).all()
    assert len(entries) == 1

    # Exactly one idempotency record must exist
    stmt_rec = select(IdempotencyRecord).where(IdempotencyRecord.key == idempotency_key)
    records = (await db_session.scalars(stmt_rec)).all()
    assert len(records) == 1


@pytest.mark.asyncio
async def test_service_level_idempotency_collision_with_different_payload(
    db_session: AsyncSession, test_wallet: Wallet
) -> None:
    """Validate that using the same idempotency key with different payload raises DuplicateTransactionException."""
    # Seed 1000 credits
    await WalletService.execute_transaction(
        db=db_session,
        wallet_id=test_wallet.id,
        amount=1000,
        entry_type=LedgerEntryType.CREDIT,
    )

    idempotency_key = f"collision-key-{uuid.uuid4()}"

    # Initial transaction
    await WalletService.execute_transaction(
        db=db_session,
        wallet_id=test_wallet.id,
        amount=200,
        entry_type=LedgerEntryType.DEBIT,
        idempotency_key=idempotency_key,
    )

    # Collision attempt with different amount (400 instead of 200)
    with pytest.raises(DuplicateTransactionException) as exc_info:
        await WalletService.execute_transaction(
            db=db_session,
            wallet_id=test_wallet.id,
            amount=400,
            entry_type=LedgerEntryType.DEBIT,
            idempotency_key=idempotency_key,
        )

    assert exc_info.value.status_code == 400
    assert "different parameters" in exc_info.value.message

    # Collision attempt with different entry type (CREDIT instead of DEBIT)
    with pytest.raises(DuplicateTransactionException):
        await WalletService.execute_transaction(
            db=db_session,
            wallet_id=test_wallet.id,
            amount=200,
            entry_type=LedgerEntryType.CREDIT,
            idempotency_key=idempotency_key,
        )


@pytest.mark.asyncio
async def test_api_debit_idempotency_two_consecutive_requests(
    client: httpx.AsyncClient, auth_headers: dict[str, str]
) -> None:
    """Validate two consecutive identical HTTP debit requests with same Idempotency-Key.

    Ensures the second request responds with HTTP 200, balance is deducted only once,
    and only one entry exists in the ledger.
    """
    # 1. Fund the wallet with 1000 credits
    fund_res = await client.post(
        "/api/v1/wallet/faucet",
        json={"amount": 1000},
        headers={**auth_headers, "Idempotency-Key": f"fund-{uuid.uuid4()}"},
    )
    assert fund_res.status_code == 200

    idempotency_key = f"debit-once-{uuid.uuid4()}"
    debit_payload = {"amount": 400, "description": "Spin bet"}

    # 2. First debit request
    res1 = await client.post(
        "/api/v1/wallet/debit",
        json=debit_payload,
        headers={**auth_headers, "Idempotency-Key": idempotency_key},
    )
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["balance_before"] == 1000
    assert data1["balance_after"] == 600
    assert data1["amount"] == 400
    entry_id = data1["id"]

    # 3. Second identical debit request
    res2 = await client.post(
        "/api/v1/wallet/debit",
        json=debit_payload,
        headers={**auth_headers, "Idempotency-Key": idempotency_key},
    )
    assert res2.status_code == 200
    data2 = res2.json()
    # Response must match previous transaction
    assert data2["id"] == entry_id
    assert data2["balance_after"] == 600

    # 4. Verify wallet balance remains exactly 600
    wallet_res = await client.get("/api/v1/wallet", headers=auth_headers)
    assert wallet_res.status_code == 200
    assert wallet_res.json()["balance"] == 600

    # 5. Verify ledger has exactly 2 entries (1 faucet + 1 debit)
    ledger_res = await client.get("/api/v1/wallet/ledger", headers=auth_headers)
    assert ledger_res.status_code == 200
    entries = ledger_res.json()
    assert len(entries) == 2


@pytest.mark.asyncio
async def test_api_idempotency_payload_mismatch_returns_400(
    client: httpx.AsyncClient, auth_headers: dict[str, str]
) -> None:
    """Validate that resending the same Idempotency-Key with different payload returns HTTP 400."""
    idempotency_key = f"mismatch-{uuid.uuid4()}"

    # First request: 500
    res1 = await client.post(
        "/api/v1/wallet/faucet",
        json={"amount": 500},
        headers={**auth_headers, "Idempotency-Key": idempotency_key},
    )
    assert res1.status_code == 200

    # Second request: 1000 with SAME key
    res2 = await client.post(
        "/api/v1/wallet/faucet",
        json={"amount": 1000},
        headers={**auth_headers, "Idempotency-Key": idempotency_key},
    )
    assert res2.status_code == 400
    assert "different parameters" in res2.json()["detail"]
