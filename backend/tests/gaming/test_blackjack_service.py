"""Integration tests for Classic Blackjack Gaming Service, FSM states, and transactional ledger settlements.

Simulación de Blackjack Clásico con fines didácticos. Módulo no apto para operaciones con dinero real.
"""
import uuid

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.gaming.engines.blackjack import (
    BlackjackAction,
    BlackjackStatus,
)
from app.modules.gaming.engines.rng import DeterministicRNGProvider
from app.modules.gaming.exceptions import (
    GameRoundAlreadySettledException,
    InvalidBlackjackActionException,
)
from app.modules.gaming.models import GameSession
from app.modules.gaming.services import GamingService
from app.modules.identity.models import User
from app.modules.wallet.enums import LedgerEntryType
from app.modules.wallet.exceptions import InsufficientFundsException
from app.modules.wallet.models import LedgerEntry, Wallet
from app.modules.wallet.services import WalletService


@pytest.mark.asyncio
async def test_blackjack_double_down_debits_twice_and_settles(
    db_session: AsyncSession,
    test_user: User,
    test_wallet: Wallet,
    test_blackjack_session: GameSession,
) -> None:
    """Test DOUBLE_DOWN flow:

    Verifies:
    - Initial deal debits 100 credits (BET_SIMULATION).
    - Player receives 5 + 6 = 11 (2 cards, can_double=True).
    - Double down debits another 100 credits (total 200 debited in two BET_SIMULATION entries).
    - Player receives exactly 1 card: a 10 (total 21).
    - Dealer stands on 18.
    - Player wins 21 vs 18 -> payout 400 (2.0x total bet of 200).
    - Wallet balance mutates: 500 - 100 - 100 + 400 = 700 credits.
    - Exactly two BET_SIMULATION and one WIN_SIMULATION entries recorded for round.
    """
    # 1. Deposit initial 500 credits
    await WalletService.execute_transaction(
        db=db_session,
        wallet_id=test_wallet.id,
        amount=500,
        entry_type=LedgerEntryType.CREDIT,
        description="Initial deposit for blackjack double test",
    )
    assert test_wallet.balance == 500

    # 2. Deterministic deal:
    # Shoe: 3 is HEARTS 5, 8 is HEARTS 10, 3 (next) is HEARTS 6, 6 is HEARTS 8
    # Player: 5 + 6 = 11; Dealer: 10 + 8 = 18
    deal_rng = DeterministicRNGProvider([3, 8, 3, 6])

    deal_resp = await GamingService.start_blackjack_round(
        db=db_session,
        user_id=test_user.id,
        session_id=test_blackjack_session.id,
        bet_amount=100,
        rng=deal_rng,
    )

    assert deal_resp.status == BlackjackStatus.IN_PROGRESS
    assert deal_resp.initial_bet == 100
    assert deal_resp.total_bet == 100
    assert deal_resp.can_double is True
    assert deal_resp.is_settled is False
    assert deal_resp.player_score == 11
    assert deal_resp.dealer_score is None  # Hole card censored
    assert deal_resp.dealer_cards[1].hidden is True
    assert deal_resp.current_balance == 400  # 500 - 100

    # 3. Process DOUBLE_DOWN:
    # Player draws a 10 (index 7 in remaining shoe) -> 11 + 10 = 21
    # Dealer has 18 >= 17, stands
    action_rng = DeterministicRNGProvider([7])

    action_resp = await GamingService.process_blackjack_action(
        db=db_session,
        user_id=test_user.id,
        round_id=deal_resp.round_id,
        action=BlackjackAction.DOUBLE_DOWN,
        rng=action_rng,
    )

    assert action_resp.status == BlackjackStatus.PLAYER_WON
    assert action_resp.initial_bet == 100
    assert action_resp.total_bet == 200
    assert action_resp.can_double is False
    assert action_resp.is_settled is True
    assert action_resp.player_score == 21
    assert action_resp.dealer_score == 20
    assert action_resp.dealer_cards[1].hidden is False  # Hole card revealed
    assert action_resp.payout_amount == 400
    assert action_resp.current_balance == 700  # 400 - 100 + 400 = 700

    # 4. Verify wallet and ledger records in database
    await db_session.refresh(test_wallet)
    assert test_wallet.balance == 700

    stmt_ledger = (
        select(LedgerEntry)
        .where(
            LedgerEntry.wallet_id == test_wallet.id,
            LedgerEntry.reference_id == deal_resp.round_id,
        )
        .order_by(LedgerEntry.created_at.asc())
    )
    entries = list((await db_session.scalars(stmt_ledger)).all())
    assert len(entries) == 3

    # Check two separate BET_SIMULATION entries for the same initial amount (100)
    bet_entries = [e for e in entries if e.entry_type == LedgerEntryType.BET_SIMULATION]
    assert len(bet_entries) == 2
    assert bet_entries[0].amount == 100
    assert bet_entries[1].amount == 100

    # Check WIN_SIMULATION entry
    win_entries = [e for e in entries if e.entry_type == LedgerEntryType.WIN_SIMULATION]
    assert len(win_entries) == 1
    assert win_entries[0].amount == 400


@pytest.mark.asyncio
async def test_blackjack_rejection_of_action_on_finalized_round(
    db_session: AsyncSession,
    test_user: User,
    test_wallet: Wallet,
    test_blackjack_session: GameSession,
) -> None:
    """Test rejection of player actions on an already completed round (prevents re-play and cheating)."""
    # 1. Deposit 500 credits
    await WalletService.execute_transaction(
        db=db_session,
        wallet_id=test_wallet.id,
        amount=500,
        entry_type=LedgerEntryType.CREDIT,
    )

    # 2. Start round with deterministic cards:
    # Player: 10 + 9 = 19; Dealer: 10 + 8 = 18
    deal_rng = DeterministicRNGProvider([8, 8, 7, 6])
    deal_resp = await GamingService.start_blackjack_round(
        db=db_session,
        user_id=test_user.id,
        session_id=test_blackjack_session.id,
        bet_amount=100,
        rng=deal_rng,
    )
    assert deal_resp.status == BlackjackStatus.IN_PROGRESS

    # 3. Player stands -> Round finalizes
    stand_resp = await GamingService.process_blackjack_action(
        db=db_session,
        user_id=test_user.id,
        round_id=deal_resp.round_id,
        action=BlackjackAction.STAND,
    )
    assert stand_resp.is_settled is True
    assert stand_resp.status == BlackjackStatus.PLAYER_WON

    # 4. Attempting HIT on the finished round must raise GameRoundAlreadySettledException
    with pytest.raises(GameRoundAlreadySettledException) as exc_hit:
        await GamingService.process_blackjack_action(
            db=db_session,
            user_id=test_user.id,
            round_id=deal_resp.round_id,
            action=BlackjackAction.HIT,
        )
    assert exc_hit.value.status_code == 400

    # 5. Attempting DOUBLE_DOWN on the finished round must also be rejected
    with pytest.raises(GameRoundAlreadySettledException) as exc_dd:
        await GamingService.process_blackjack_action(
            db=db_session,
            user_id=test_user.id,
            round_id=deal_resp.round_id,
            action=BlackjackAction.DOUBLE_DOWN,
        )
    assert exc_dd.value.status_code == 400

    # 6. Attempting STAND on the finished round must also be rejected
    with pytest.raises(GameRoundAlreadySettledException) as exc_stand:
        await GamingService.process_blackjack_action(
            db=db_session,
            user_id=test_user.id,
            round_id=deal_resp.round_id,
            action=BlackjackAction.STAND,
        )
    assert exc_stand.value.status_code == 400


@pytest.mark.asyncio
async def test_blackjack_rejection_of_hit_after_busting(
    db_session: AsyncSession,
    test_user: User,
    test_wallet: Wallet,
    test_blackjack_session: GameSession,
) -> None:
    """Test that once a player busts (> 21) on HIT, the round settles and subsequent actions are rejected."""
    # 1. Deposit 500 credits
    await WalletService.execute_transaction(
        db=db_session,
        wallet_id=test_wallet.id,
        amount=500,
        entry_type=LedgerEntryType.CREDIT,
    )

    # 2. Player dealt 10 + 6 = 16
    deal_rng = DeterministicRNGProvider([8, 8, 4, 6])
    deal_resp = await GamingService.start_blackjack_round(
        db=db_session,
        user_id=test_user.id,
        session_id=test_blackjack_session.id,
        bet_amount=100,
        rng=deal_rng,
    )
    assert deal_resp.player_score == 16
    assert deal_resp.status == BlackjackStatus.IN_PROGRESS

    # 3. Player hits and draws 10 (index 6 in remaining shoe) -> 16 + 10 = 26 (Busted)
    hit_rng = DeterministicRNGProvider([6])
    hit_resp = await GamingService.process_blackjack_action(
        db=db_session,
        user_id=test_user.id,
        round_id=deal_resp.round_id,
        action=BlackjackAction.HIT,
        rng=hit_rng,
    )

    assert hit_resp.status == BlackjackStatus.PLAYER_BUSTED
    assert hit_resp.player_score == 26
    assert hit_resp.is_settled is True
    assert hit_resp.payout_amount == 0

    # 4. Attempting another HIT after busting must be rejected
    with pytest.raises(GameRoundAlreadySettledException) as exc_info:
        await GamingService.process_blackjack_action(
            db=db_session,
            user_id=test_user.id,
            round_id=deal_resp.round_id,
            action=BlackjackAction.HIT,
        )
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_blackjack_natural_blackjack_on_deal_settles_immediately(
    db_session: AsyncSession,
    test_user: User,
    test_wallet: Wallet,
    test_blackjack_session: GameSession,
) -> None:
    """Player receives natural Blackjack on deal -> settled immediately with 2.5x payout."""
    await WalletService.execute_transaction(
        db=db_session,
        wallet_id=test_wallet.id,
        amount=500,
        entry_type=LedgerEntryType.CREDIT,
    )

    # Player: Ace + King = 21 (natural BJ); Dealer: 10 + 8 = 18
    deal_rng = DeterministicRNGProvider([12, 8, 10, 6])

    resp = await GamingService.start_blackjack_round(
        db=db_session,
        user_id=test_user.id,
        session_id=test_blackjack_session.id,
        bet_amount=100,
        rng=deal_rng,
    )

    assert resp.status == BlackjackStatus.BLACKJACK
    assert resp.is_settled is True
    assert resp.payout_amount == 250  # 100 * 2.5
    assert resp.current_balance == 650  # 500 - 100 + 250 = 650
    assert resp.dealer_score == 18
    assert resp.dealer_cards[1].hidden is False


@pytest.mark.asyncio
async def test_blackjack_double_down_rejected_when_more_than_two_cards(
    db_session: AsyncSession,
    test_user: User,
    test_wallet: Wallet,
    test_blackjack_session: GameSession,
) -> None:
    """Verify DOUBLE_DOWN is rejected with HTTP 400 if player already drew a third card."""
    await WalletService.execute_transaction(
        db=db_session,
        wallet_id=test_wallet.id,
        amount=500,
        entry_type=LedgerEntryType.CREDIT,
    )

    # Player: 2 + 3 = 5; Dealer: 10 + 8 = 18
    deal_rng = DeterministicRNGProvider([0, 8, 0, 6])
    deal_resp = await GamingService.start_blackjack_round(
        db=db_session,
        user_id=test_user.id,
        session_id=test_blackjack_session.id,
        bet_amount=100,
        rng=deal_rng,
    )

    # First hit: player draws a 4 (now 3 cards, score 9)
    hit_rng = DeterministicRNGProvider([0])
    hit_resp = await GamingService.process_blackjack_action(
        db=db_session,
        user_id=test_user.id,
        round_id=deal_resp.round_id,
        action=BlackjackAction.HIT,
        rng=hit_rng,
    )
    assert len(hit_resp.player_cards) == 3
    assert hit_resp.can_double is False

    # Attempt double down on 3 cards
    with pytest.raises(InvalidBlackjackActionException) as exc_info:
        await GamingService.process_blackjack_action(
            db=db_session,
            user_id=test_user.id,
            round_id=deal_resp.round_id,
            action=BlackjackAction.DOUBLE_DOWN,
        )
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_blackjack_double_down_rejected_when_insufficient_funds(
    db_session: AsyncSession,
    test_user: User,
    test_wallet: Wallet,
    test_blackjack_session: GameSession,
) -> None:
    """Verify DOUBLE_DOWN fails if player cannot afford the second bet amount."""
    # Deposit exactly 100 credits
    await WalletService.execute_transaction(
        db=db_session,
        wallet_id=test_wallet.id,
        amount=100,
        entry_type=LedgerEntryType.CREDIT,
    )
    assert test_wallet.balance == 100

    # Deal debits all 100 credits -> balance is now 0
    deal_rng = DeterministicRNGProvider([3, 8, 3, 6])
    deal_resp = await GamingService.start_blackjack_round(
        db=db_session,
        user_id=test_user.id,
        session_id=test_blackjack_session.id,
        bet_amount=100,
        rng=deal_rng,
    )
    assert deal_resp.current_balance == 0

    # Attempt DOUBLE_DOWN without funds
    with pytest.raises(InsufficientFundsException):
        await GamingService.process_blackjack_action(
            db=db_session,
            user_id=test_user.id,
            round_id=deal_resp.round_id,
            action=BlackjackAction.DOUBLE_DOWN,
        )


@pytest.mark.asyncio
async def test_blackjack_api_endpoints_deal_and_action(
    client: httpx.AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    test_wallet: Wallet,
    test_blackjack_session: GameSession,
    auth_headers: dict[str, str],
) -> None:
    """Verify Blackjack REST API endpoints:

    - POST /api/v1/games/sessions/{session_id}/blackjack/deal
    - POST /api/v1/games/rounds/{round_id}/blackjack/action
    """
    # 1. Deposit 1000 credits
    await WalletService.execute_transaction(
        db=db_session,
        wallet_id=test_wallet.id,
        amount=1000,
        entry_type=LedgerEntryType.CREDIT,
    )

    # 2. Call deal endpoint
    deal_headers = {
        **auth_headers,
        "Idempotency-Key": f"api-bj-deal-{uuid.uuid4()}",
    }
    deal_url = f"/api/v1/games/sessions/{test_blackjack_session.id}/blackjack/deal"
    deal_resp = await client.post(deal_url, json={"bet_amount": 50}, headers=deal_headers)

    assert deal_resp.status_code == 200, deal_resp.text
    deal_data = deal_resp.json()
    assert "round_id" in deal_data
    assert deal_data["initial_bet"] == 50
    assert len(deal_data["player_cards"]) == 2
    assert len(deal_data["dealer_cards"]) == 2
    round_id = deal_data["round_id"]

    # If game didn't finish on deal with natural BJ, execute STAND
    if not deal_data["is_settled"]:
        action_url = f"/api/v1/games/rounds/{round_id}/blackjack/action"
        action_resp = await client.post(action_url, json={"action": "STAND"}, headers=auth_headers)
        assert action_resp.status_code == 200, action_resp.text
        action_data = action_resp.json()
        assert action_data["is_settled"] is True
        assert action_data["dealer_score"] is not None
        assert action_data["dealer_cards"][1]["hidden"] is False
