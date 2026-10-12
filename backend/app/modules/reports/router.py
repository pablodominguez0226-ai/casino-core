"""Reporting & Operational Analytics API router.

All endpoints strictly operate on simulated virtual credits (CREDITS / VIRTUAL).
Protected under granular RBAC permission 'reports:read'.
"""
from datetime import datetime
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.modules.identity.dependencies import require_permission
from app.modules.identity.models import User
from app.modules.reports.schemas import (
    DailyTrendsResponse,
    DateRangeFilterParams,
    GamePerformanceReportResponse,
    OverviewMetricsResponse,
    WalletFlowReportResponse,
)
from app.modules.reports.services import ReportingService

router = APIRouter(prefix="/reports", tags=["reports"])


def _resolve_tenant_operator_id(
    current_user: User,
    requested_operator_id: uuid.UUID | None,
) -> uuid.UUID | None:
    """Enforce strict multi-tenant boundary unless authenticated actor has global SUPER_ADMIN."""
    user_roles = {r.name for r in current_user.roles}
    user_perms = {p.code for r in current_user.roles for p in r.permissions}

    is_super = "SUPER_ADMIN" in user_roles or "system:admin" in user_perms
    if not is_super:
        return current_user.operator_id

    # SUPER_ADMIN may inspect a specific tenant or query platform-wide (None)
    return requested_operator_id


@router.get(
    "/overview",
    response_model=OverviewMetricsResponse,
    summary="Get consolidated operational metrics",
)
async def get_overview(
    from_date: datetime | None = Query(None, description="Start date UTC (defaults to 30 days ago)"),
    to_date: datetime | None = Query(None, description="End date UTC (defaults to current UTC)"),
    operator_id: uuid.UUID | None = Query(None, description="Filter by operator UUID (SUPER_ADMIN only)"),
    current_user: User = Depends(require_permission("reports:read")),
    db: AsyncSession = Depends(get_db_session),
) -> OverviewMetricsResponse:
    """Retrieve high-level operational KPIs for the tenant operator."""
    date_filter = DateRangeFilterParams(from_date=from_date, to_date=to_date)
    if date_filter.from_date > date_filter.to_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="from_date cannot be later than to_date",
        )

    target_operator_id = _resolve_tenant_operator_id(current_user, operator_id)

    return await ReportingService.get_overview_metrics(
        db=db,
        operator_id=target_operator_id,
        from_date=date_filter.from_date,
        to_date=date_filter.to_date,
    )


@router.get(
    "/games",
    response_model=GamePerformanceReportResponse,
    summary="Get game performance and observed RTP report",
)
async def get_games_performance(
    from_date: datetime | None = Query(None, description="Start date UTC (defaults to 30 days ago)"),
    to_date: datetime | None = Query(None, description="End date UTC (defaults to current UTC)"),
    operator_id: uuid.UUID | None = Query(None, description="Filter by operator UUID (SUPER_ADMIN only)"),
    current_user: User = Depends(require_permission("reports:read")),
    db: AsyncSession = Depends(get_db_session),
) -> GamePerformanceReportResponse:
    """Retrieve catalog performance breakdown with turnover, winnings, observed RTP, and hold."""
    date_filter = DateRangeFilterParams(from_date=from_date, to_date=to_date)
    if date_filter.from_date > date_filter.to_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="from_date cannot be later than to_date",
        )

    target_operator_id = _resolve_tenant_operator_id(current_user, operator_id)

    return await ReportingService.get_game_performance(
        db=db,
        operator_id=target_operator_id,
        from_date=date_filter.from_date,
        to_date=date_filter.to_date,
    )


@router.get(
    "/wallet-flow",
    response_model=WalletFlowReportResponse,
    summary="Get aggregated virtual credit flow report",
)
async def get_wallet_flow(
    from_date: datetime | None = Query(None, description="Start date UTC (defaults to 30 days ago)"),
    to_date: datetime | None = Query(None, description="End date UTC (defaults to current UTC)"),
    operator_id: uuid.UUID | None = Query(None, description="Filter by operator UUID (SUPER_ADMIN only)"),
    current_user: User = Depends(require_permission("reports:read")),
    db: AsyncSession = Depends(get_db_session),
) -> WalletFlowReportResponse:
    """Retrieve ledger movements aggregated by entry type, minted credits, and burned credits."""
    date_filter = DateRangeFilterParams(from_date=from_date, to_date=to_date)
    if date_filter.from_date > date_filter.to_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="from_date cannot be later than to_date",
        )

    target_operator_id = _resolve_tenant_operator_id(current_user, operator_id)

    return await ReportingService.get_wallet_flow(
        db=db,
        operator_id=target_operator_id,
        from_date=date_filter.from_date,
        to_date=date_filter.to_date,
    )


@router.get(
    "/trends",
    response_model=DailyTrendsResponse,
    summary="Get daily activity historical trends",
)
async def get_daily_trends(
    days: int = Query(14, ge=1, le=90, description="Number of past days for trend series"),
    operator_id: uuid.UUID | None = Query(None, description="Filter by operator UUID (SUPER_ADMIN only)"),
    current_user: User = Depends(require_permission("reports:read")),
    db: AsyncSession = Depends(get_db_session),
) -> DailyTrendsResponse:
    """Retrieve daily time-series activity points for analytical charting."""
    target_operator_id = _resolve_tenant_operator_id(current_user, operator_id)

    return await ReportingService.get_daily_trends(
        db=db,
        operator_id=target_operator_id,
        days=days,
    )
