import asyncio
import uuid

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.wallet.enums import LedgerEntryType
from app.modules.wallet.exceptions import InsufficientFundsException
from app.modules.wallet.models import Wallet
from app.modules.wallet.services import WalletService
from tests.wallet.conftest import TestSessionLocal


@pytest.mark.asyncio
async def test_concurrency_race_condition_double_spend_http_api(
    client: httpx.AsyncClient, auth_headers: dict[str, str]
) -> None:
    """Obligatory concurrency test: Initial balance = 1,000 credits.

    Launch two simultaneous debit requests of 800 credits each via asyncio.gather.
    Rigorously verify:
    - Exactly one request succeeds with HTTP 200 OK.
    - Exactly one request is rejected with HTTP 409 Conflict (insufficient funds).
    - Final database balance is exactly 200 credits without inconsistencies.
    """
    # 1. Fund wallet with 1,000 credits
    fund_res = await client.post(
        "/api/v1/wallet/faucet",
        json={"amount": 1000},
        headers={**auth_headers, "Idempotency-Key": f"fund-{uuid.uuid4()}"},
    )
    assert fund_res.status_code == 200
    assert fund_res.json()["balance_after"] == 1000

    # 2. Fire two concurrent debit requests of 800 credits each
    key1 = f"concurrent-debit-{uuid.uuid4()}"
    key2 = f"concurrent-debit-{uuid.uuid4()}"

    task1 = client.post(
        "/api/v1/wallet/debit",
        json={"amount": 800, "description": "Concurrent debit 1"},
        headers={**auth_headers, "Idempotency-Key": key1},
    )
    task2 = client.post(
        "/api/v1/wallet/debit",
        json={"amount": 800, "description": "Concurrent debit 2"},
        headers={**auth_headers, "Idempotency-Key": key2},
    )

    responses = await asyncio.gather(task1, task2)

    status_codes = [r.status_code for r in responses]

    # Exactly one 200 OK and exactly one 409 Conflict
    assert 200 in status_codes, f"Expected a 200 response, got {status_codes}"
    assert 409 in status_codes, f"Expected a 409 response, got {status_codes}"
    assert sorted(status_codes) == [200, 409]

    # Inspect the 409 response detail
    failed_response = [r for r in responses if r.status_code == 409][0]
    assert "Insufficient funds" in failed_response.json()["detail"]

    # 3. Check that final wallet balance is exactly 200 credits
    wallet_res = await client.get("/api/v1/wallet", headers=auth_headers)
    assert wallet_res.status_code == 200
    assert wallet_res.json()["balance"] == 200

    # 4. Verify reconciliation consistency
    reconcile_res = await client.get("/api/v1/wallet/reconcile", headers=auth_headers)
    assert reconcile_res.status_code == 200
    rec_data = reconcile_res.json()
    assert rec_data["cached_balance"] == 200
    assert rec_data["calculated_ledger_balance"] == 200
    assert rec_data["is_consistent"] is True


@pytest.mark.asyncio
async def test_concurrency_race_condition_service_level(
    db_session: AsyncSession, test_wallet: Wallet
) -> None:
    """Validate concurrency protection directly at WalletService level with separate sessions."""
    # Seed 1000 credits
    await WalletService.execute_transaction(
        db=db_session,
        wallet_id=test_wallet.id,
        amount=1000,
        entry_type=LedgerEntryType.CREDIT,
    )
    await db_session.refresh(test_wallet)
    assert test_wallet.balance == 1000

    results = []
    errors = []

    async def execute_debit(amount: int, key: str) -> None:
        async with TestSessionLocal() as session:
            try:
                entry = await WalletService.execute_transaction(
                    db=session,
                    wallet_id=test_wallet.id,
                    amount=amount,
                    entry_type=LedgerEntryType.DEBIT,
                    idempotency_key=key,
                )
                results.append(entry)
            except Exception as e:
                errors.append(e)

    # Launch two simultaneous debits of 800 credits
    key1 = f"svc-conc-{uuid.uuid4()}"
    key2 = f"svc-conc-{uuid.uuid4()}"

    await asyncio.gather(
        execute_debit(800, key1),
        execute_debit(800, key2),
    )

    # Exactly one succeeded and one failed
    assert len(results) == 1
    assert len(errors) == 1
    assert isinstance(errors[0], InsufficientFundsException)
    assert errors[0].status_code == 409

    # Verify final balance is exactly 200 in a fresh session
    async with TestSessionLocal() as fresh_session:
        refreshed_wallet = await WalletService.get_wallet_by_id(fresh_session, test_wallet.id)
        assert refreshed_wallet.balance == 200

        # And reconciliation passes
        rec = await WalletService.reconcile_wallet(fresh_session, test_wallet.id)
        assert rec.cached_balance == 200
        assert rec.calculated_ledger_balance == 200
        assert rec.is_consistent is True


@pytest.mark.asyncio
async def test_concurrency_identical_idempotency_key_parallel_requests(
    client: httpx.AsyncClient, auth_headers: dict[str, str]
) -> None:
    """Validate that two identical concurrent requests with the SAME idempotency key.

    Both return successfully (200 OK) without double deduction.
    """
    # 1. Fund wallet with 1,000 credits
    await client.post(
        "/api/v1/wallet/faucet",
        json={"amount": 1000},
        headers={**auth_headers, "Idempotency-Key": f"fund-{uuid.uuid4()}"},
    )

    # 2. Fire two concurrent debit requests with the EXACT SAME key
    shared_key = f"same-key-{uuid.uuid4()}"

    task1 = client.post(
        "/api/v1/wallet/debit",
        json={"amount": 300, "description": "Duplicate concurrent bet"},
        headers={**auth_headers, "Idempotency-Key": shared_key},
    )
    task2 = client.post(
        "/api/v1/wallet/debit",
        json={"amount": 300, "description": "Duplicate concurrent bet"},
        headers={**auth_headers, "Idempotency-Key": shared_key},
    )

    responses = await asyncio.gather(task1, task2)

    # Both requests succeed
    assert responses[0].status_code == 200
    assert responses[1].status_code == 200

    # Final balance must be 700 (1000 - 300), NOT 400!
    wallet_res = await client.get("/api/v1/wallet", headers=auth_headers)
    assert wallet_res.status_code == 200
    assert wallet_res.json()["balance"] == 700
