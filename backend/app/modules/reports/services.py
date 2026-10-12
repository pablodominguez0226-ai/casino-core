"""Analytical reporting service for tenant operational metrics and gaming intelligence.

Strictly operates on simulated virtual credits (CREDITS / VIRTUAL). No real-money transactions.
"""
from datetime import datetime, timedelta, timezone
import logging
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.gaming.models import Game, GameRound, GameSession
from app.modules.identity.models import User
from app.modules.reports.schemas import (
    DailyTrendPoint,
    DailyTrendsResponse,
    GamePerformanceItem,
    GamePerformanceReportResponse,
    OverviewMetricsResponse,
    WalletFlowItem,
    WalletFlowReportResponse,
)
from app.modules.wallet.models import LedgerEntry, Wallet

logger = logging.getLogger(__name__)


class ReportingService:
    """Service providing aggregated analytical queries and domain formula calculations."""

    @classmethod
    async def get_overview_metrics(
        cls,
        db: AsyncSession,
        operator_id: uuid.UUID | None,
        from_date: datetime,
        to_date: datetime,
    ) -> OverviewMetricsResponse:
        """Calculate consolidated operational metrics across users, sessions, rounds, and wallets."""
        if from_date.tzinfo is None:
            from_date = from_date.replace(tzinfo=timezone.utc)
        if to_date.tzinfo is None:
            to_date = to_date.replace(tzinfo=timezone.utc)

        # 1. Total registered players
        user_stmt = select(func.count(User.id))
        if operator_id is not None:
            user_stmt = user_stmt.where(User.operator_id == operator_id)
        total_players = int(await db.scalar(user_stmt) or 0)

        # 2. Daily Active Users (DAU) in the last 24 hours
        dau_threshold = datetime.now(timezone.utc) - timedelta(hours=24)

        dau_rounds_stmt = (
            select(GameSession.user_id)
            .select_from(GameRound)
            .join(GameSession, GameRound.session_id == GameSession.id)
            .join(User, GameSession.user_id == User.id)
            .where(GameRound.created_at >= dau_threshold)
        )
        if operator_id is not None:
            dau_rounds_stmt = dau_rounds_stmt.where(User.operator_id == operator_id)

        dau_sessions_stmt = (
            select(GameSession.user_id)
            .select_from(GameSession)
            .join(User, GameSession.user_id == User.id)
            .where(GameSession.started_at >= dau_threshold)
        )
        if operator_id is not None:
            dau_sessions_stmt = dau_sessions_stmt.where(User.operator_id == operator_id)

        dau_union = dau_rounds_stmt.union(dau_sessions_stmt).subquery()
        daily_active_users = int(await db.scalar(select(func.count()).select_from(dau_union)) or 0)

        # 3. Total sessions initiated in the specified period
        session_stmt = (
            select(func.count(GameSession.id))
            .select_from(GameSession)
            .join(User, GameSession.user_id == User.id)
            .where(
                GameSession.started_at >= from_date,
                GameSession.started_at <= to_date,
            )
        )
        if operator_id is not None:
            session_stmt = session_stmt.where(User.operator_id == operator_id)
        total_sessions = int(await db.scalar(session_stmt) or 0)

        # 4. Total rounds, turnover, payout in the period
        round_stmt = (
            select(
                func.count(GameRound.id).label("total_rounds"),
                func.coalesce(func.sum(GameRound.bet_amount), 0).label("turnover"),
                func.coalesce(func.sum(GameRound.payout_amount), 0).label("payout"),
            )
            .select_from(GameRound)
            .join(GameSession, GameRound.session_id == GameSession.id)
            .join(User, GameSession.user_id == User.id)
            .where(
                GameRound.created_at >= from_date,
                GameRound.created_at <= to_date,
            )
        )
        if operator_id is not None:
            round_stmt = round_stmt.where(User.operator_id == operator_id)

        round_res = (await db.execute(round_stmt)).one()
        total_game_rounds = int(round_res.total_rounds or 0)
        total_turnover_credits = int(round_res.turnover or 0)
        total_payout_credits = int(round_res.payout or 0)

        # Simulated GGR = Bet Turnover - Payout
        simulated_ggr_credits = total_turnover_credits - total_payout_credits

        # Observed RTP (%) = (Payout / Turnover) * 100
        if total_turnover_credits > 0:
            overall_observed_rtp = round(
                (float(total_payout_credits) / float(total_turnover_credits)) * 100.0,
                2,
            )
        else:
            overall_observed_rtp = 0.0

        # 5. Circulating virtual credits across all wallets
        wallet_stmt = select(func.coalesce(func.sum(Wallet.balance), 0)).select_from(Wallet)
        if operator_id is not None:
            wallet_stmt = wallet_stmt.where(Wallet.operator_id == operator_id)
        circulating_virtual_credits = int(await db.scalar(wallet_stmt) or 0)

        return OverviewMetricsResponse(
            total_players=total_players,
            daily_active_users=daily_active_users,
            total_sessions=total_sessions,
            total_game_rounds=total_game_rounds,
            total_turnover_credits=total_turnover_credits,
            total_payout_credits=total_payout_credits,
            simulated_ggr_credits=simulated_ggr_credits,
            overall_observed_rtp=overall_observed_rtp,
            circulating_virtual_credits=circulating_virtual_credits,
        )

    @classmethod
    async def get_game_performance(
        cls,
        db: AsyncSession,
        operator_id: uuid.UUID | None,
        from_date: datetime,
        to_date: datetime,
    ) -> GamePerformanceReportResponse:
        """Aggregate rounds by game catalog item, computing turnover, winnings, observed RTP, and hold."""
        if from_date.tzinfo is None:
            from_date = from_date.replace(tzinfo=timezone.utc)
        if to_date.tzinfo is None:
            to_date = to_date.replace(tzinfo=timezone.utc)

        # Subquery aggregating game rounds by game_id within the date range
        round_subquery = (
            select(
                GameSession.game_id.label("game_id"),
                func.count(GameRound.id).label("rounds_played"),
                func.coalesce(func.sum(GameRound.bet_amount), 0).label("total_bet"),
                func.coalesce(func.sum(GameRound.payout_amount), 0).label("total_won"),
            )
            .select_from(GameRound)
            .join(GameSession, GameRound.session_id == GameSession.id)
            .where(
                GameRound.created_at >= from_date,
                GameRound.created_at <= to_date,
            )
            .group_by(GameSession.game_id)
            .subquery()
        )

        stmt = (
            select(
                Game.id.label("game_id"),
                Game.code.label("game_code"),
                Game.name.label("game_name"),
                func.coalesce(round_subquery.c.rounds_played, 0).label("rounds_played"),
                func.coalesce(round_subquery.c.total_bet, 0).label("total_bet"),
                func.coalesce(round_subquery.c.total_won, 0).label("total_won"),
            )
            .select_from(Game)
            .outerjoin(round_subquery, Game.id == round_subquery.c.game_id)
        )
        if operator_id is not None:
            stmt = stmt.where(Game.operator_id == operator_id)

        stmt = stmt.order_by(
            func.coalesce(round_subquery.c.total_bet, 0).desc(),
            Game.name.asc(),
        )

        result = await db.execute(stmt)
        items: list[GamePerformanceItem] = []

        for row in result.all():
            total_bet = int(row.total_bet or 0)
            total_won = int(row.total_won or 0)
            simulated_ggr = total_bet - total_won

            if total_bet > 0:
                observed_rtp = round((float(total_won) / float(total_bet)) * 100.0, 2)
                hold_percentage = round(100.0 - observed_rtp, 2)
            else:
                observed_rtp = 0.0
                hold_percentage = 100.0

            items.append(
                GamePerformanceItem(
                    game_id=row.game_id,
                    game_code=row.game_code,
                    game_name=row.game_name,
                    rounds_played=int(row.rounds_played or 0),
                    total_bet=total_bet,
                    total_won=total_won,
                    simulated_ggr=simulated_ggr,
                    observed_rtp=observed_rtp,
                    hold_percentage=hold_percentage,
                )
            )

        return GamePerformanceReportResponse(items=items)

    @classmethod
    async def get_wallet_flow(
        cls,
        db: AsyncSession,
        operator_id: uuid.UUID | None,
        from_date: datetime,
        to_date: datetime,
    ) -> WalletFlowReportResponse:
        """Aggregate ledger entries by transaction type, calculating emitted and absorbed credit volumes."""
        if from_date.tzinfo is None:
            from_date = from_date.replace(tzinfo=timezone.utc)
        if to_date.tzinfo is None:
            to_date = to_date.replace(tzinfo=timezone.utc)

        stmt = (
            select(
                LedgerEntry.entry_type,
                func.count(LedgerEntry.id).label("entry_count"),
                func.coalesce(func.sum(LedgerEntry.amount), 0).label("volume"),
            )
            .select_from(LedgerEntry)
            .join(Wallet, LedgerEntry.wallet_id == Wallet.id)
            .where(
                LedgerEntry.created_at >= from_date,
                LedgerEntry.created_at <= to_date,
            )
        )
        if operator_id is not None:
            stmt = stmt.where(Wallet.operator_id == operator_id)

        stmt = stmt.group_by(LedgerEntry.entry_type).order_by(LedgerEntry.entry_type.asc())

        result = await db.execute(stmt)
        flows: list[WalletFlowItem] = []
        volumes: dict[str, int] = {}

        for row in result.all():
            entry_type_str = row.entry_type.value if hasattr(row.entry_type, "value") else str(row.entry_type)
            count_val = int(row.entry_count or 0)
            vol_val = int(row.volume or 0)

            flows.append(
                WalletFlowItem(
                    entry_type=entry_type_str,
                    count=count_val,
                    total_volume=vol_val,
                )
            )
            volumes[entry_type_str] = vol_val

        # Total Minted: virtual credits introduced via deposits/faucets and bonuses
        total_minted = volumes.get("CREDIT", 0) + volumes.get("BONUS", 0)

        # Total Burned or Lost: explicit withdrawals/debits + net virtual losses in gaming
        net_game_loss = max(0, volumes.get("BET_SIMULATION", 0) - volumes.get("WIN_SIMULATION", 0))
        total_burned_or_lost = volumes.get("DEBIT", 0) + net_game_loss

        return WalletFlowReportResponse(
            flows=flows,
            total_minted=total_minted,
            total_burned_or_lost=total_burned_or_lost,
        )

    @classmethod
    async def get_daily_trends(
        cls,
        db: AsyncSession,
        operator_id: uuid.UUID | None,
        days: int = 14,
    ) -> DailyTrendsResponse:
        """Generate historical daily activity series using date_trunc over game rounds."""
        start_date = datetime.now(timezone.utc) - timedelta(days=days)
        day_col = func.date_trunc("day", GameRound.created_at).label("day")

        stmt = (
            select(
                day_col,
                func.count(func.distinct(GameSession.user_id)).label("active_users"),
                func.count(GameRound.id).label("rounds"),
                func.coalesce(func.sum(GameRound.bet_amount), 0).label("turnover"),
                func.coalesce(func.sum(GameRound.payout_amount), 0).label("payout"),
            )
            .select_from(GameRound)
            .join(GameSession, GameRound.session_id == GameSession.id)
            .join(User, GameSession.user_id == User.id)
            .where(GameRound.created_at >= start_date)
        )
        if operator_id is not None:
            stmt = stmt.where(User.operator_id == operator_id)

        stmt = stmt.group_by(day_col).order_by(day_col.asc())

        result = await db.execute(stmt)
        trends: list[DailyTrendPoint] = []

        for row in result.all():
            day_val = row.day
            if hasattr(day_val, "strftime"):
                date_str = day_val.strftime("%Y-%m-%d")
            else:
                date_str = str(day_val)[:10]

            trends.append(
                DailyTrendPoint(
                    date=date_str,
                    active_users=int(row.active_users or 0),
                    rounds=int(row.rounds or 0),
                    turnover=int(row.turnover or 0),
                    payout=int(row.payout or 0),
                )
            )

        return DailyTrendsResponse(trends=trends)
