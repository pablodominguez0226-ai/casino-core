"""Integration tests for GamingService and Gaming API endpoints.

Simulación educativa. RNG no apto ni certificado para juego con dinero real.
"""
import uuid

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.gaming.engines.rng import DeterministicRNGProvider
from app.modules.gaming.enums import GameSessionStatus
from app.modules.gaming.exceptions import (
    GameSessionInactiveException,
    GameSessionNotFoundException,
    InvalidBetAmountException,
)
from app.modules.gaming.models import Game, GameRound, GameSession
from app.modules.gaming.services import GamingService
from app.modules.identity.models import User
from app.modules.operators.models import Operator
from app.modules.wallet.enums import LedgerEntryType
from app.modules.wallet.exceptions import InsufficientFundsException
from app.modules.wallet.models import LedgerEntry, Wallet
from app.modules.wallet.services import WalletService


@pytest.mark.asyncio
async def test_spin_successful_with_win_and_atomic_ledger_entries(
    db_session: AsyncSession,
    test_user: User,
    test_wallet: Wallet,
    test_game: Game,
    test_session: GameSession,
) -> None:
    """Validate full spin cycle: debit bet, resolve RNG jackpot, credit payout, persist GameRound."""
    # 1. Fund wallet with 1,000 credits
    await WalletService.execute_transaction(
        db=db_session,
        wallet_id=test_wallet.id,
        amount=1000,
        entry_type=LedgerEntryType.CREDIT,
    )
    await db_session.refresh(test_wallet)
    assert test_wallet.balance == 1000

    # 2. Configure deterministic RNG yielding 3 SEVENs (Jackpot 100x)
    rng = DeterministicRNGProvider([4, 4, 4])
    bet_amount = 50

    # 3. Execute spin
    response = await GamingService.execute_spin(
        db=db_session,
        user_id=test_user.id,
        session_id=test_session.id,
        bet_amount=bet_amount,
        rng=rng,
    )

    # 4. Verify spin response
    assert response.bet_amount == 50
    assert response.payout_amount == 5000  # 50 * 100
    assert response.is_win is True
    assert response.symbols == ["SEVEN", "SEVEN", "SEVEN"]
    # Final balance: 1000 - 50 + 5000 = 5950
    assert response.current_balance == 5950

    await db_session.refresh(test_wallet)
    assert test_wallet.balance == 5950

    # 5. Verify GameRound persistence
    stmt_round = select(GameRound).where(GameRound.id == response.round_id)
    saved_round = await db_session.scalar(stmt_round)
    assert saved_round is not None
    assert saved_round.session_id == test_session.id
    assert saved_round.bet_amount == 50
    assert saved_round.payout_amount == 5000
    assert saved_round.round_data["multiplier"] == 100
    assert saved_round.round_data["stops"] == [4, 4, 4]

    # 6. Verify Ledger movements: 1 CREDIT (fund), 1 BET_SIMULATION, 1 WIN_SIMULATION
    stmt_entries = (
        select(LedgerEntry)
        .where(LedgerEntry.wallet_id == test_wallet.id)
        .order_by(LedgerEntry.created_at.asc())
    )
    entries = list((await db_session.scalars(stmt_entries)).all())
    assert len(entries) == 3
    assert entries[0].entry_type == LedgerEntryType.CREDIT
    assert entries[1].entry_type == LedgerEntryType.BET_SIMULATION
    assert entries[1].amount == 50
    assert entries[1].balance_before == 1000
    assert entries[1].balance_after == 950
    assert entries[2].entry_type == LedgerEntryType.WIN_SIMULATION
    assert entries[2].amount == 5000
    assert entries[2].balance_before == 950
    assert entries[2].balance_after == 5950


@pytest.mark.asyncio
async def test_spin_losing_cycle_no_win_entry(
    db_session: AsyncSession,
    test_user: User,
    test_wallet: Wallet,
    test_game: Game,
    test_session: GameSession,
) -> None:
    """Validate spin with losing outcome: only BET_SIMULATION is logged, balance deducted."""
    await WalletService.execute_transaction(
        db=db_session,
        wallet_id=test_wallet.id,
        amount=500,
        entry_type=LedgerEntryType.CREDIT,
    )

    rng = DeterministicRNGProvider([0, 1, 2])  # Non-matching symbols
    bet_amount = 50

    response = await GamingService.execute_spin(
        db=db_session,
        user_id=test_user.id,
        session_id=test_session.id,
        bet_amount=bet_amount,
        rng=rng,
    )

    assert response.is_win is False
    assert response.payout_amount == 0
    assert response.current_balance == 450

    await db_session.refresh(test_wallet)
    assert test_wallet.balance == 450

    # Ledger entries: 1 CREDIT, 1 BET_SIMULATION
    stmt_entries = (
        select(LedgerEntry)
        .where(LedgerEntry.wallet_id == test_wallet.id)
        .order_by(LedgerEntry.created_at.asc())
    )
    entries = list((await db_session.scalars(stmt_entries)).all())
    assert len(entries) == 2
    assert entries[1].entry_type == LedgerEntryType.BET_SIMULATION


@pytest.mark.asyncio
async def test_spin_rejected_insufficient_funds_no_round_created(
    db_session: AsyncSession,
    test_user: User,
    test_wallet: Wallet,
    test_game: Game,
    test_session: GameSession,
) -> None:
    """Validate that spin fails when wallet balance is insufficient, leaving no GameRound."""
    await db_session.refresh(test_wallet)
    assert test_wallet.balance == 0

    session_id = test_session.id
    wallet_id = test_wallet.id
    user_id = test_user.id

    with pytest.raises(InsufficientFundsException):
        await GamingService.execute_spin(
            db=db_session,
            user_id=user_id,
            session_id=session_id,
            bet_amount=100,
        )

    # Balance must remain 0
    refreshed_wallet = await db_session.get(Wallet, wallet_id)
    assert refreshed_wallet is not None
    assert refreshed_wallet.balance == 0

    # No rounds must exist
    stmt_rounds = select(GameRound).where(GameRound.session_id == session_id)
    rounds = list((await db_session.scalars(stmt_rounds)).all())
    assert len(rounds) == 0

    # No ledger entries must exist
    stmt_entries = select(LedgerEntry).where(LedgerEntry.wallet_id == wallet_id)
    entries = list((await db_session.scalars(stmt_entries)).all())
    assert len(entries) == 0


@pytest.mark.asyncio
async def test_spin_rejected_inactive_session(
    db_session: AsyncSession,
    test_user: User,
    test_wallet: Wallet,
    test_game: Game,
    test_session: GameSession,
) -> None:
    """Validate that spin is rejected if game session is already completed/inactive."""
    await WalletService.execute_transaction(
        db=db_session,
        wallet_id=test_wallet.id,
        amount=500,
        entry_type=LedgerEntryType.CREDIT,
    )

    # End session
    await GamingService.end_session(
        db=db_session,
        session_id=test_session.id,
        user_id=test_user.id,
    )

    with pytest.raises(GameSessionInactiveException):
        await GamingService.execute_spin(
            db=db_session,
            user_id=test_user.id,
            session_id=test_session.id,
            bet_amount=50,
        )


@pytest.mark.asyncio
async def test_spin_rejected_invalid_bet_limits(
    db_session: AsyncSession,
    test_user: User,
    test_wallet: Wallet,
    test_game: Game,
    test_session: GameSession,
) -> None:
    """Validate that bet amounts below min_bet or above max_bet are rejected."""
    await WalletService.execute_transaction(
        db=db_session,
        wallet_id=test_wallet.id,
        amount=5000,
        entry_type=LedgerEntryType.CREDIT,
    )

    # min_bet is 10, max_bet is 1000
    with pytest.raises(InvalidBetAmountException):
        await GamingService.execute_spin(
            db=db_session,
            user_id=test_user.id,
            session_id=test_session.id,
            bet_amount=5,
        )

    with pytest.raises(InvalidBetAmountException):
        await GamingService.execute_spin(
            db=db_session,
            user_id=test_user.id,
            session_id=test_session.id,
            bet_amount=1500,
        )


@pytest.mark.asyncio
async def test_api_games_lifecycle_and_spin_endpoints(
    client: httpx.AsyncClient,
    auth_headers: dict[str, str],
    test_game: Game,
) -> None:
    """Validate HTTP API flows: list games, start session, spin with idempotency, fetch rounds, end session."""
    # 1. Deposit 2,000 credits via faucet
    faucet_res = await client.post(
        "/api/v1/wallet/faucet",
        json={"amount": 2000},
        headers={**auth_headers, "Idempotency-Key": f"faucet-{uuid.uuid4()}"},
    )
    assert faucet_res.status_code == 200

    # 2. List active games
    games_res = await client.get("/api/v1/games", headers=auth_headers)
    assert games_res.status_code == 200
    games = games_res.json()
    assert len(games) >= 1
    assert any(g["code"] == "CLASSIC_FRUIT_SLOT" for g in games)

    # 3. Start a new game session
    session_res = await client.post(
        "/api/v1/games/sessions",
        json={"game_id": str(test_game.id)},
        headers=auth_headers,
    )
    assert session_res.status_code == 201
    session_data = session_res.json()
    session_id = session_data["id"]
    assert session_data["status"] == GameSessionStatus.ACTIVE.value

    # 4. First spin with Idempotency-Key
    spin_idempotency_key = f"spin-key-{uuid.uuid4()}"
    spin_res1 = await client.post(
        f"/api/v1/games/sessions/{session_id}/spin",
        json={"bet_amount": 50},
        headers={**auth_headers, "Idempotency-Key": spin_idempotency_key},
    )
    assert spin_res1.status_code == 200
    data1 = spin_res1.json()
    assert data1["bet_amount"] == 50
    assert len(data1["symbols"]) == 3
    round1_id = data1["round_id"]
    balance_after_spin1 = data1["current_balance"]

    # 5. Second spin with IDENTICAL Idempotency-Key must return same result without re-debiting
    spin_res2 = await client.post(
        f"/api/v1/games/sessions/{session_id}/spin",
        json={"bet_amount": 50},
        headers={**auth_headers, "Idempotency-Key": spin_idempotency_key},
    )
    assert spin_res2.status_code == 200
    data2 = spin_res2.json()
    assert data2["round_id"] == round1_id
    assert data2["current_balance"] == balance_after_spin1

    # Verify wallet balance directly
    wallet_res = await client.get("/api/v1/wallet", headers=auth_headers)
    assert wallet_res.status_code == 200
    assert wallet_res.json()["balance"] == balance_after_spin1

    # 6. Get session rounds history
    rounds_res = await client.get(
        f"/api/v1/games/sessions/{session_id}/rounds",
        headers=auth_headers,
    )
    assert rounds_res.status_code == 200
    rounds = rounds_res.json()
    assert len(rounds) == 1
    assert rounds[0]["id"] == round1_id
    assert rounds[0]["bet_amount"] == 50

    # 7. End session
    end_res = await client.post(
        f"/api/v1/games/sessions/{session_id}/end",
        headers=auth_headers,
    )
    assert end_res.status_code == 200
    assert end_res.json()["status"] == GameSessionStatus.COMPLETED.value
    assert end_res.json()["ended_at"] is not None

    # 8. Spin on ended session must fail with HTTP 400
    spin_res3 = await client.post(
        f"/api/v1/games/sessions/{session_id}/spin",
        json={"bet_amount": 50},
        headers={**auth_headers, "Idempotency-Key": f"spin-after-end-{uuid.uuid4()}"},
    )
    assert spin_res3.status_code == 400
    assert "not active" in spin_res3.json()["detail"]


@pytest.mark.asyncio
async def test_gaming_service_errors_and_edge_cases(
    db_session: AsyncSession,
    test_user: User,
    test_wallet: Wallet,
    test_game: Game,
    test_session: GameSession,
) -> None:
    """Validate error conditions in GamingService: invalid game, invalid session, and idempotency collision."""
    from app.modules.gaming.exceptions import GameNotFoundException
    from app.modules.wallet.exceptions import DuplicateTransactionException
    from app.modules.wallet.models import IdempotencyRecord

    # 1. Non-existent game
    fake_game_id = uuid.uuid4()
    with pytest.raises(GameNotFoundException):
        await GamingService.start_session(db_session, test_user.id, fake_game_id)

    # 2. Non-existent session
    fake_session_id = uuid.uuid4()
    with pytest.raises(GameSessionNotFoundException):
        await GamingService.get_session(db_session, fake_session_id, test_user.id)

    with pytest.raises(GameSessionNotFoundException):
        await GamingService.execute_spin(
            db=db_session,
            user_id=test_user.id,
            session_id=fake_session_id,
            bet_amount=50,
        )

    # 3. Idempotency collision with different parameters
    idempotency_key = f"collision-test-{uuid.uuid4()}"
    record = IdempotencyRecord(
        key=idempotency_key,
        wallet_id=test_wallet.id,
        response_status=200,
        response_payload={
            "session_id": str(test_session.id),
            "bet_amount": 100,
            "round_id": str(uuid.uuid4()),
            "symbols": ["SEVEN", "SEVEN", "SEVEN"],
            "payout_amount": 10000,
            "is_win": True,
            "current_balance": 10000,
        },
    )
    db_session.add(record)
    await db_session.commit()

    with pytest.raises(DuplicateTransactionException):
        await GamingService.execute_spin(
            db=db_session,
            user_id=test_user.id,
            session_id=test_session.id,
            bet_amount=50,  # 50 != 100 in record
            idempotency_key=idempotency_key,
        )


@pytest.mark.asyncio
async def test_gaming_seed_defaults(
    db_session: AsyncSession,
    test_operator: Operator,
) -> None:
    """Validate seed_default_games function."""
    from app.modules.gaming.seed import seed_default_games

    games = await seed_default_games(db_session, test_operator.id)
    assert len(games) >= 1
    assert games[0].code == "CLASSIC_FRUIT_SLOT"

    # Running again idempotently should not duplicate
    games_again = await seed_default_games(db_session, test_operator.id)
    assert len(games_again) == 0


def test_gaming_models_repr(test_game: Game, test_session: GameSession) -> None:
    """Validate string representations of Gaming models."""
    assert "CLASSIC_FRUIT_SLOT" in repr(test_game)
    assert "GameSession" in repr(test_session)

    round_obj = GameRound(
        id=uuid.uuid4(),
        session_id=test_session.id,
        bet_amount=10,
        payout_amount=20,
        round_data={"test": 1},
    )
    assert "GameRound" in repr(round_obj)

