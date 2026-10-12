"""Integration tests for European Roulette Gaming Service and transactional settlements.

Simulación de Ruleta Europea para fines educativos. RNG no certificado para apuestas reales.
"""
import uuid

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.gaming.engines.rng import DeterministicRNGProvider
from app.modules.gaming.enums import GameSessionStatus, RouletteBetType
from app.modules.gaming.exceptions import (
    GameSessionInactiveException,
    GamingException,
    InvalidBetAmountException,
    InvalidRouletteBetException,
)
from app.modules.gaming.models import GameRound, GameSession
from app.modules.gaming.schemas import RouletteBetRequest
from app.modules.gaming.services import GamingService
from app.modules.identity.models import User
from app.modules.wallet.enums import LedgerEntryType
from app.modules.wallet.exceptions import DuplicateTransactionException, InsufficientFundsException
from app.modules.wallet.models import LedgerEntry, Wallet
from app.modules.wallet.services import WalletService


@pytest.mark.asyncio
async def test_roulette_spin_successful_multi_bet_atomic_ledger_entries(
    db_session: AsyncSession,
    test_user: User,
    test_wallet: Wallet,
    test_roulette_session: GameSession,
) -> None:
    """User bets 100 on RED and 50 on BLACK (total bet = 150 credits).

    Verifies:
    - Exactly 150 credits are debited from the wallet.
    - Deterministic RNG forces winning number 1 (Red).
    - RED wins 200 (100 * 2x), BLACK loses (0). Total payout = 200.
    - Wallet balance increases by net 50 credits (credited 200).
    - Database contains corresponding BET_SIMULATION and WIN_SIMULATION ledger entries.
    - GameRound record is committed with complete breakdown in round_data.
    """
    # 1. Deposit 500 initial credits into wallet
    await WalletService.execute_transaction(
        db=db_session,
        wallet_id=test_wallet.id,
        amount=500,
        entry_type=LedgerEntryType.CREDIT,
        description="Initial deposit for roulette test",
    )
    assert test_wallet.balance == 500

    # 2. Setup deterministic RNG yielding 1 (Red)
    rng = DeterministicRNGProvider([1])
    bets = [
        RouletteBetRequest(bet_type=RouletteBetType.RED, amount=100),
        RouletteBetRequest(bet_type=RouletteBetType.BLACK, amount=50),
    ]

    response = await GamingService.execute_roulette_spin(
        db=db_session,
        user_id=test_user.id,
        session_id=test_roulette_session.id,
        bets=bets,
        rng=rng,
    )

    # 3. Assert response structure and math
    assert response.winning_number == 1
    assert response.color == "RED"
    assert response.total_bet == 150
    assert response.total_payout == 200
    assert response.current_balance == 550  # 500 - 150 + 200
    assert len(response.resolutions) == 2

    res_red = response.resolutions[0]
    assert res_red.bet_type == "RED"
    assert res_red.won is True
    assert res_red.payout == 200

    res_black = response.resolutions[1]
    assert res_black.bet_type == "BLACK"
    assert res_black.won is False
    assert res_black.payout == 0

    # 4. Verify wallet balance and ledger entries in database
    await db_session.refresh(test_wallet)
    assert test_wallet.balance == 550

    stmt_ledger = (
        select(LedgerEntry)
        .where(LedgerEntry.wallet_id == test_wallet.id)
        .order_by(LedgerEntry.created_at.asc())
    )
    ledger_entries = list((await db_session.scalars(stmt_ledger)).all())
    # Should have: 1. DEPOSIT (500), 2. BET_SIMULATION (150), 3. WIN_SIMULATION (200)
    assert len(ledger_entries) == 3
    assert ledger_entries[1].entry_type == LedgerEntryType.BET_SIMULATION
    assert ledger_entries[1].amount == 150
    assert ledger_entries[1].balance_after == 350
    assert ledger_entries[2].entry_type == LedgerEntryType.WIN_SIMULATION
    assert ledger_entries[2].amount == 200
    assert ledger_entries[2].balance_after == 550

    # 5. Verify GameRound entity persisted in DB
    round_record = await db_session.get(GameRound, response.round_id)
    assert round_record is not None
    assert round_record.session_id == test_roulette_session.id
    assert round_record.bet_amount == 150
    assert round_record.payout_amount == 200
    assert round_record.round_data["winning_number"] == 1
    assert round_record.round_data["color"] == "RED"
    assert len(round_record.round_data["resolutions"]) == 2
    assert "Simulación de Ruleta Europea" in round_record.round_data["disclaimer"]


@pytest.mark.asyncio
async def test_roulette_spin_rejected_insufficient_funds_combined_bets(
    db_session: AsyncSession,
    test_user: User,
    test_wallet: Wallet,
    test_roulette_session: GameSession,
) -> None:
    """User has 100 credits but bets 100 on Red and 50 on Black (total 150).

    Verifies:
    - Operation raises InsufficientFundsException.
    - Transaction is rolled back: wallet balance remains intact at 100.
    - No GameRound entity is created.
    - No BET_SIMULATION entry is recorded.
    """
    await WalletService.execute_transaction(
        db=db_session,
        wallet_id=test_wallet.id,
        amount=100,
        entry_type=LedgerEntryType.CREDIT,
        description="Deposit 100 credits",
    )
    assert test_wallet.balance == 100

    session_id = test_roulette_session.id
    wallet_id = test_wallet.id
    user_id = test_user.id

    bets = [
        RouletteBetRequest(bet_type=RouletteBetType.RED, amount=100),
        RouletteBetRequest(bet_type=RouletteBetType.BLACK, amount=50),
    ]

    with pytest.raises(InsufficientFundsException):
        await GamingService.execute_roulette_spin(
            db=db_session,
            user_id=user_id,
            session_id=session_id,
            bets=bets,
            rng=DeterministicRNGProvider([1]),
        )

    # Balance remains 100
    refreshed_wallet = await db_session.get(Wallet, wallet_id)
    assert refreshed_wallet is not None
    assert refreshed_wallet.balance == 100

    # No round created
    stmt_rounds = select(GameRound).where(GameRound.session_id == session_id)
    rounds = list((await db_session.scalars(stmt_rounds)).all())
    assert len(rounds) == 0

    # Only initial deposit entry in ledger
    stmt_ledger = select(LedgerEntry).where(LedgerEntry.wallet_id == wallet_id)
    ledger_entries = list((await db_session.scalars(stmt_ledger)).all())
    assert len(ledger_entries) == 1
    assert ledger_entries[0].entry_type == LedgerEntryType.CREDIT


@pytest.mark.asyncio
async def test_roulette_spin_all_losing_cycle_no_win_entry(
    db_session: AsyncSession,
    test_user: User,
    test_wallet: Wallet,
    test_roulette_session: GameSession,
) -> None:
    """User places bets that both lose (e.g. on 0 green).

    Verifies:
    - Wallet is debited.
    - No WIN_SIMULATION entry is generated.
    - GameRound has payout_amount = 0.
    """
    await WalletService.execute_transaction(
        db=db_session,
        wallet_id=test_wallet.id,
        amount=300,
        entry_type=LedgerEntryType.CREDIT,
    )

    rng = DeterministicRNGProvider([0])  # Green 0
    bets = [
        RouletteBetRequest(bet_type=RouletteBetType.RED, amount=50),
        RouletteBetRequest(bet_type=RouletteBetType.EVEN, amount=50),
    ]

    response = await GamingService.execute_roulette_spin(
        db=db_session,
        user_id=test_user.id,
        session_id=test_roulette_session.id,
        bets=bets,
        rng=rng,
    )

    assert response.winning_number == 0
    assert response.color == "GREEN"
    assert response.total_bet == 100
    assert response.total_payout == 0
    assert response.current_balance == 200

    await db_session.refresh(test_wallet)
    assert test_wallet.balance == 200

    stmt_ledger = (
        select(LedgerEntry)
        .where(LedgerEntry.wallet_id == test_wallet.id)
        .order_by(LedgerEntry.created_at.asc())
    )
    ledger_entries = list((await db_session.scalars(stmt_ledger)).all())
    assert len(ledger_entries) == 2  # Deposit + BET_SIMULATION only
    assert ledger_entries[1].entry_type == LedgerEntryType.BET_SIMULATION
    assert ledger_entries[1].amount == 100


@pytest.mark.asyncio
async def test_roulette_spin_rejected_inactive_session(
    db_session: AsyncSession,
    test_user: User,
    test_roulette_session: GameSession,
) -> None:
    """Rejects roulette spin on COMPLETED session."""
    test_roulette_session.status = GameSessionStatus.COMPLETED
    await db_session.commit()

    bets = [RouletteBetRequest(bet_type=RouletteBetType.RED, amount=10)]
    with pytest.raises(GameSessionInactiveException):
        await GamingService.execute_roulette_spin(
            db=db_session,
            user_id=test_user.id,
            session_id=test_roulette_session.id,
            bets=bets,
        )


@pytest.mark.asyncio
async def test_roulette_spin_rejected_non_roulette_game(
    db_session: AsyncSession,
    test_user: User,
    test_session: GameSession,
) -> None:
    """Rejects execute_roulette_spin on a SLOT session."""
    bets = [RouletteBetRequest(bet_type=RouletteBetType.RED, amount=10)]
    with pytest.raises(GamingException, match="not a roulette game"):
        await GamingService.execute_roulette_spin(
            db=db_session,
            user_id=test_user.id,
            session_id=test_session.id,
            bets=bets,
        )


@pytest.mark.asyncio
async def test_roulette_spin_rejected_bet_limits(
    db_session: AsyncSession,
    test_user: User,
    test_roulette_session: GameSession,
) -> None:
    """Rejects bet if total_bet is below game.min_bet (5) or above game.max_bet (5000)."""
    # Below min_bet
    bets_too_low = [RouletteBetRequest(bet_type=RouletteBetType.RED, amount=2)]
    with pytest.raises(InvalidBetAmountException):
        await GamingService.execute_roulette_spin(
            db=db_session,
            user_id=test_user.id,
            session_id=test_roulette_session.id,
            bets=bets_too_low,
        )

    # Above max_bet
    bets_too_high = [RouletteBetRequest(bet_type=RouletteBetType.RED, amount=6000)]
    with pytest.raises(InvalidBetAmountException):
        await GamingService.execute_roulette_spin(
            db=db_session,
            user_id=test_user.id,
            session_id=test_roulette_session.id,
            bets=bets_too_high,
        )


@pytest.mark.asyncio
async def test_roulette_spin_idempotency_replay(
    db_session: AsyncSession,
    test_user: User,
    test_wallet: Wallet,
    test_roulette_session: GameSession,
) -> None:
    """Replaying a spin with the same Idempotency-Key returns the cached response without double-debiting."""
    await WalletService.execute_transaction(
        db=db_session,
        wallet_id=test_wallet.id,
        amount=500,
        entry_type=LedgerEntryType.CREDIT,
    )

    idempotency_key = f"roulette-idemp-{uuid.uuid4()}"
    bets = [RouletteBetRequest(bet_type=RouletteBetType.RED, amount=50)]

    res1 = await GamingService.execute_roulette_spin(
        db=db_session,
        user_id=test_user.id,
        session_id=test_roulette_session.id,
        bets=bets,
        idempotency_key=idempotency_key,
        rng=DeterministicRNGProvider([1]),  # 1 Red
    )

    balance_after_res1 = res1.current_balance

    # Second call with the same idempotency key
    res2 = await GamingService.execute_roulette_spin(
        db=db_session,
        user_id=test_user.id,
        session_id=test_roulette_session.id,
        bets=bets,
        idempotency_key=idempotency_key,
        rng=DeterministicRNGProvider([2]),  # Won't be called
    )

    assert res1.round_id == res2.round_id
    assert res1.winning_number == res2.winning_number
    assert res1.current_balance == res2.current_balance

    await db_session.refresh(test_wallet)
    assert test_wallet.balance == balance_after_res1

    # Calling with different parameters and same key raises DuplicateTransactionException
    with pytest.raises(DuplicateTransactionException):
        await GamingService.execute_roulette_spin(
            db=db_session,
            user_id=test_user.id,
            session_id=test_roulette_session.id,
            bets=[RouletteBetRequest(bet_type=RouletteBetType.RED, amount=100)],
            idempotency_key=idempotency_key,
        )


@pytest.mark.asyncio
async def test_api_roulette_spin_endpoint(
    client: httpx.AsyncClient,
    db_session: AsyncSession,
    test_wallet: Wallet,
    test_roulette_session: GameSession,
    auth_headers: dict[str, str],
) -> None:
    """End-to-end HTTP integration test via POST /api/v1/games/sessions/{id}/roulette/spin."""
    await WalletService.execute_transaction(
        db=db_session,
        wallet_id=test_wallet.id,
        amount=1000,
        entry_type=LedgerEntryType.CREDIT,
    )

    headers = {
        **auth_headers,
        "Idempotency-Key": f"api-roulette-{uuid.uuid4()}",
    }
    payload = {
        "bets": [
            {"bet_type": "RED", "amount": 100, "numbers": []},
            {"bet_type": "STRAIGHT_UP", "amount": 20, "numbers": [17]},
        ]
    }

    url = f"/api/v1/games/sessions/{test_roulette_session.id}/roulette/spin"
    resp = await client.post(url, json=payload, headers=headers)

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "round_id" in data
    assert 0 <= data["winning_number"] <= 36
    assert data["color"] in ("GREEN", "RED", "BLACK")
    assert data["total_bet"] == 120
    assert "total_payout" in data
    assert "current_balance" in data
    assert len(data["resolutions"]) == 2


@pytest.mark.asyncio
async def test_roulette_spin_rejected_invalid_roulette_bet(
    db_session: AsyncSession,
    test_user: User,
    test_roulette_session: GameSession,
) -> None:
    """Rejects spin when bet parameters violate European roulette rules."""
    # Bet on invalid number 99
    bets = [RouletteBetRequest(bet_type=RouletteBetType.STRAIGHT_UP, numbers=[99], amount=10)]
    with pytest.raises(InvalidRouletteBetException, match="Invalid roulette number"):
        await GamingService.execute_roulette_spin(
            db=db_session,
            user_id=test_user.id,
            session_id=test_roulette_session.id,
            bets=bets,
        )

