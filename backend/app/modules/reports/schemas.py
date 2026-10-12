"""Pydantic v2 schemas for the Reporting & Operational Analytics Engine.

Strictly refers to simulated credits (CREDITS / VIRTUAL). No real currency.
"""
from datetime import datetime, timedelta, timezone
import uuid

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DateRangeFilterParams(BaseModel):
    """Query parameters for temporal report filtering.

    Defaults to a 30-day window ending at the current UTC timestamp.
    """

    from_date: datetime | None = Field(
        default=None,
        description="Filter range start date (UTC). Defaults to 30 days prior.",
    )
    to_date: datetime | None = Field(
        default=None,
        description="Filter range end date (UTC). Defaults to current UTC timestamp.",
    )

    @model_validator(mode="after")
    def populate_defaults_and_timezones(self) -> "DateRangeFilterParams":
        """Ensure timezone-awareness and populate default 30-day window."""
        now = datetime.now(timezone.utc)
        if self.to_date is None:
            self.to_date = now
        elif self.to_date.tzinfo is None:
            self.to_date = self.to_date.replace(tzinfo=timezone.utc)

        if self.from_date is None:
            self.from_date = self.to_date - timedelta(days=30)
        elif self.from_date.tzinfo is None:
            self.from_date = self.from_date.replace(tzinfo=timezone.utc)

        return self


class OverviewMetricsResponse(BaseModel):
    """Consolidated executive overview metrics for tenant operations."""

    model_config = ConfigDict(from_attributes=True)

    total_players: int = Field(description="Total registered players under operator")
    daily_active_users: int = Field(description="Daily active users (DAU) in last 24h")
    total_sessions: int = Field(description="Total game sessions initiated in period")
    total_game_rounds: int = Field(description="Total game rounds executed in period")
    total_turnover_credits: int = Field(description="Total simulated bet turnover in credits")
    total_payout_credits: int = Field(description="Total simulated winnings paid in credits")
    simulated_ggr_credits: int = Field(description="Simulated Gross Gaming Revenue (Turnover - Payout)")
    overall_observed_rtp: float = Field(description="Overall observed Return-To-Player percentage")
    circulating_virtual_credits: int = Field(description="Current total balance of all operator wallets")


class GamePerformanceItem(BaseModel):
    """Performance breakdown for an individual game title."""

    model_config = ConfigDict(from_attributes=True)

    game_id: uuid.UUID
    game_code: str
    game_name: str
    rounds_played: int
    total_bet: int
    total_won: int
    simulated_ggr: int
    observed_rtp: float
    hold_percentage: float


class GamePerformanceReportResponse(BaseModel):
    """Aggregated game performance catalog report."""

    model_config = ConfigDict(from_attributes=True)

    items: list[GamePerformanceItem]


class WalletFlowItem(BaseModel):
    """Aggregate breakdown by ledger transaction movement type."""

    model_config = ConfigDict(from_attributes=True)

    entry_type: str
    count: int
    total_volume: int


class WalletFlowReportResponse(BaseModel):
    """Consolidated audit report of virtual credit emission and movements."""

    model_config = ConfigDict(from_attributes=True)

    flows: list[WalletFlowItem]
    total_minted: int = Field(description="Credits minted via deposits/faucets and bonuses")
    total_burned_or_lost: int = Field(description="Credits burned via debits or net gaming loss")


class DailyTrendPoint(BaseModel):
    """Daily operational trend metrics datapoint."""

    model_config = ConfigDict(from_attributes=True)

    date: str = Field(description="Date formatted as YYYY-MM-DD")
    active_users: int = Field(description="Distinct active users on this date")
    rounds: int = Field(description="Game rounds played on this date")
    turnover: int = Field(description="Total simulated turnover on this date")
    payout: int = Field(description="Total simulated payout on this date")


class DailyTrendsResponse(BaseModel):
    """Time-series trend report for activity charting."""

    model_config = ConfigDict(from_attributes=True)

    trends: list[DailyTrendPoint]
