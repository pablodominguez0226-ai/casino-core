"""Tests for ReportingService domain queries and analytical formulas."""
from datetime import datetime, timedelta, timezone
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.gaming.enums import GameSessionStatus, GameType
from app.modules.gaming.models import Game, GameRound, GameSession
from app.modules.identity.models import User
from app.modules.operators.models import Operator
from app.modules.reports.services import ReportingService
from app.modules.wallet.enums import LedgerEntryType
from app.modules.wallet.models import LedgerEntry, Wallet


@pytest.mark.asyncio
async def test_overview_metrics_calculations(
    db_session: AsyncSession,
    test_operator: Operator,
    player_user: User,
) -> None:
    """Validate GGR, Observed RTP, DAU, and circulating credits calculations."""
    now = datetime.now(timezone.utc)
    from_date = now - timedelta(days=7)
    to_date = now + timedelta(hours=1)

    # 1. Setup Wallet with balance
    wallet = Wallet(
        user_id=player_user.id,
        operator_id=test_operator.id,
        balance=15000,
        currency="CREDITS",
    )
    db_session.add(wallet)

    # 2. Setup Game
    game = Game(
        operator_id=test_operator.id,
        code="SLOT_TEST_1",
        name="Test Slot Machine",
        game_type=GameType.SLOT,
        min_bet=10,
        max_bet=1000,
        config={},
        is_active=True,
    )
    db_session.add(game)
    await db_session.flush()

    # 3. Setup GameSession
    session = GameSession(
        user_id=player_user.id,
        game_id=game.id,
        status=GameSessionStatus.ACTIVE,
        started_at=now - timedelta(hours=2),
    )
    db_session.add(session)
    await db_session.flush()

    # 4. Setup GameRounds:
    # Round 1: Bet 1000, Won 800
    round1 = GameRound(
        session_id=session.id,
        bet_amount=1000,
        payout_amount=800,
        round_data={"result": "cherry"},
        created_at=now - timedelta(hours=1),
    )
    # Round 2: Bet 500, Won 100
    round2 = GameRound(
        session_id=session.id,
        bet_amount=500,
        payout_amount=100,
        round_data={"result": "lemon"},
        created_at=now - timedelta(minutes=30),
    )
    db_session.add(round1)
    db_session.add(round2)
    await db_session.commit()

    # Execute service
    overview = await ReportingService.get_overview_metrics(
        db=db_session,
        operator_id=test_operator.id,
        from_date=from_date,
        to_date=to_date,
    )

    # Validations
    assert overview.total_players >= 1
    assert overview.daily_active_users == 1
    assert overview.total_sessions >= 1
    assert overview.total_game_rounds == 2

    # Turnover = 1000 + 500 = 1500
    assert overview.total_turnover_credits == 1500
    # Payout = 800 + 100 = 900
    assert overview.total_payout_credits == 900
    # Simulated GGR = 1500 - 900 = 600
    assert overview.simulated_ggr_credits == 600
    # Observed RTP = (900 / 1500) * 100 = 60.0%
    assert overview.overall_observed_rtp == 60.0
    # Circulating virtual credits
    assert overview.circulating_virtual_credits >= 15000


@pytest.mark.asyncio
async def test_game_performance_breakdown(
    db_session: AsyncSession,
    test_operator: Operator,
    player_user: User,
) -> None:
    """Validate per-game breakdown, observed RTP, and hold percentages."""
    now = datetime.now(timezone.utc)
    from_date = now - timedelta(days=1)
    to_date = now + timedelta(hours=1)

    # Game A
    game_a = Game(
        operator_id=test_operator.id,
        code="SLOT_ALPHA",
        name="Slot Alpha",
        game_type=GameType.SLOT,
        min_bet=10,
        max_bet=1000,
        config={},
    )
    # Game B
    game_b = Game(
        operator_id=test_operator.id,
        code="SLOT_BETA",
        name="Slot Beta",
        game_type=GameType.SLOT,
        min_bet=10,
        max_bet=1000,
        config={},
    )
    db_session.add_all([game_a, game_b])
    await db_session.flush()

    # Sessions
    session_a = GameSession(user_id=player_user.id, game_id=game_a.id)
    session_b = GameSession(user_id=player_user.id, game_id=game_b.id)
    db_session.add_all([session_a, session_b])
    await db_session.flush()

    # Rounds for Game A: Bet 1000, Won 950 (RTP 95.0%, Hold 5.0%, GGR 50)
    round_a = GameRound(
        session_id=session_a.id,
        bet_amount=1000,
        payout_amount=950,
        round_data={},
        created_at=now,
    )
    # Rounds for Game B: Bet 500, Won 100 (RTP 20.0%, Hold 80.0%, GGR 400)
    round_b = GameRound(
        session_id=session_b.id,
        bet_amount=500,
        payout_amount=100,
        round_data={},
        created_at=now,
    )
    db_session.add_all([round_a, round_b])
    await db_session.commit()

    report = await ReportingService.get_game_performance(
        db=db_session,
        operator_id=test_operator.id,
        from_date=from_date,
        to_date=to_date,
    )

    items_by_code = {item.game_code: item for item in report.items}
    assert "SLOT_ALPHA" in items_by_code
    assert "SLOT_BETA" in items_by_code

    item_a = items_by_code["SLOT_ALPHA"]
    assert item_a.rounds_played == 1
    assert item_a.total_bet == 1000
    assert item_a.total_won == 950
    assert item_a.simulated_ggr == 50
    assert item_a.observed_rtp == 95.0
    assert item_a.hold_percentage == 5.0

    item_b = items_by_code["SLOT_BETA"]
    assert item_b.rounds_played == 1
    assert item_b.total_bet == 500
    assert item_b.total_won == 100
    assert item_b.simulated_ggr == 400
    assert item_b.observed_rtp == 20.0
    assert item_b.hold_percentage == 80.0


@pytest.mark.asyncio
async def test_wallet_flow_aggregation(
    db_session: AsyncSession,
    test_operator: Operator,
    player_user: User,
) -> None:
    """Validate ledger flow aggregation, total minted, and total burned/lost."""
    now = datetime.now(timezone.utc)
    from_date = now - timedelta(days=2)
    to_date = now + timedelta(hours=1)

    wallet = Wallet(
        user_id=player_user.id,
        operator_id=test_operator.id,
        balance=8000,
        currency="CREDITS",
    )
    db_session.add(wallet)
    await db_session.flush()

    entries = [
        # Faucet / Deposit
        LedgerEntry(
            wallet_id=wallet.id,
            entry_type=LedgerEntryType.CREDIT,
            amount=5000,
            balance_before=0,
            balance_after=5000,
            created_at=now - timedelta(hours=5),
        ),
        # Bonus
        LedgerEntry(
            wallet_id=wallet.id,
            entry_type=LedgerEntryType.BONUS,
            amount=2000,
            balance_before=5000,
            balance_after=7000,
            created_at=now - timedelta(hours=4),
        ),
        # Bet Simulation
        LedgerEntry(
            wallet_id=wallet.id,
            entry_type=LedgerEntryType.BET_SIMULATION,
            amount=1500,
            balance_before=7000,
            balance_after=5500,
            created_at=now - timedelta(hours=3),
        ),
        # Win Simulation
        LedgerEntry(
            wallet_id=wallet.id,
            entry_type=LedgerEntryType.WIN_SIMULATION,
            amount=500,
            balance_before=5500,
            balance_after=6000,
            created_at=now - timedelta(hours=2),
        ),
        # Debit / Burn
        LedgerEntry(
            wallet_id=wallet.id,
            entry_type=LedgerEntryType.DEBIT,
            amount=1000,
            balance_before=6000,
            balance_after=5000,
            created_at=now - timedelta(hours=1),
        ),
    ]
    db_session.add_all(entries)
    await db_session.commit()

    report = await ReportingService.get_wallet_flow(
        db=db_session,
        operator_id=test_operator.id,
        from_date=from_date,
        to_date=to_date,
    )

    # total_minted = CREDIT (5000) + BONUS (2000) = 7000
    assert report.total_minted == 7000

    # total_burned_or_lost = DEBIT (1000) + (BET 1500 - WIN 500 = 1000 loss) = 2000
    assert report.total_burned_or_lost == 2000

    flow_types = {f.entry_type: f.total_volume for f in report.flows}
    assert flow_types["CREDIT"] == 5000
    assert flow_types["BONUS"] == 2000
    assert flow_types["BET_SIMULATION"] == 1500
    assert flow_types["WIN_SIMULATION"] == 500
    assert flow_types["DEBIT"] == 1000


@pytest.mark.asyncio
async def test_daily_trends_grouping(
    db_session: AsyncSession,
    test_operator: Operator,
    player_user: User,
) -> None:
    """Validate date_trunc grouping across days."""
    now = datetime.now(timezone.utc)
    game = Game(
        operator_id=test_operator.id,
        code="TREND_SLOT",
        name="Trend Slot",
        game_type=GameType.SLOT,
        min_bet=10,
        max_bet=1000,
        config={},
    )
    db_session.add(game)
    await db_session.flush()

    session = GameSession(user_id=player_user.id, game_id=game.id)
    db_session.add(session)
    await db_session.flush()

    # Create round today and round 2 days ago
    round_today = GameRound(
        session_id=session.id,
        bet_amount=200,
        payout_amount=50,
        round_data={},
        created_at=now,
    )
    round_past = GameRound(
        session_id=session.id,
        bet_amount=300,
        payout_amount=100,
        round_data={},
        created_at=now - timedelta(days=2),
    )
    db_session.add_all([round_today, round_past])
    await db_session.commit()

    trends = await ReportingService.get_daily_trends(
        db=db_session,
        operator_id=test_operator.id,
        days=7,
    )

    assert len(trends.trends) >= 2
    dates = [p.date for p in trends.trends]
    assert now.strftime("%Y-%m-%d") in dates
    assert (now - timedelta(days=2)).strftime("%Y-%m-%d") in dates


@pytest.mark.asyncio
async def test_multitenant_isolation_service(
    db_session: AsyncSession,
    test_operator: Operator,
    test_operator_b: Operator,
) -> None:
    """Ensure data from Operator B is strictly excluded from Operator A calculations."""
    now = datetime.now(timezone.utc)
    from_date = now - timedelta(days=1)
    to_date = now + timedelta(hours=1)

    # User B under Operator B
    user_b = User(
        operator_id=test_operator_b.id,
        email=f"userb-{uuid.uuid4().hex[:8]}@casino.com",
        hashed_password="...",
    )
    db_session.add(user_b)
    await db_session.flush()

    wallet_b = Wallet(
        user_id=user_b.id,
        operator_id=test_operator_b.id,
        balance=999999,
        currency="CREDITS",
    )
    db_session.add(wallet_b)

    game_b = Game(
        operator_id=test_operator_b.id,
        code="EXCLUSIVE_B",
        name="Exclusive B",
        game_type=GameType.SLOT,
        min_bet=10,
        max_bet=1000,
        config={},
    )
    db_session.add(game_b)
    await db_session.flush()

    session_b = GameSession(user_id=user_b.id, game_id=game_b.id)
    db_session.add(session_b)
    await db_session.flush()

    round_b = GameRound(
        session_id=session_b.id,
        bet_amount=50000,
        payout_amount=25000,
        round_data={},
        created_at=now,
    )
    db_session.add(round_b)
    await db_session.commit()

    # Query Operator A - should NOT see Operator B's data
    overview_a = await ReportingService.get_overview_metrics(
        db=db_session,
        operator_id=test_operator.id,
        from_date=from_date,
        to_date=to_date,
    )
    assert overview_a.total_turnover_credits == 0
    assert overview_a.total_payout_credits == 0
    assert overview_a.circulating_virtual_credits == 0

    # Query Game Performance for Operator A - should not list EXCLUSIVE_B
    perf_a = await ReportingService.get_game_performance(
        db=db_session,
        operator_id=test_operator.id,
        from_date=from_date,
        to_date=to_date,
    )
    assert not any(item.game_code == "EXCLUSIVE_B" for item in perf_a.items)
