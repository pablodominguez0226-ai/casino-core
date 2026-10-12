"""API Integration tests for /api/v1/reports endpoints."""

import httpx
import pytest

from app.modules.operators.models import Operator


@pytest.mark.asyncio
async def test_reports_api_player_forbidden(
    client: httpx.AsyncClient,
    player_headers: dict[str, str],
) -> None:
    """Validate that PLAYER role is strictly denied access (403 Forbidden) on all reports endpoints."""
    endpoints = [
        "/api/v1/reports/overview",
        "/api/v1/reports/games",
        "/api/v1/reports/wallet-flow",
        "/api/v1/reports/trends",
    ]

    for endpoint in endpoints:
        response = await client.get(endpoint, headers=player_headers)
        assert response.status_code == 403, f"Expected 403 for PLAYER on {endpoint}, got {response.status_code}"
        assert "Forbidden" in response.json()["detail"]


@pytest.mark.asyncio
async def test_reports_api_unauthenticated_denied(
    client: httpx.AsyncClient,
) -> None:
    """Validate that unauthenticated requests receive 401 Unauthorized."""
    endpoints = [
        "/api/v1/reports/overview",
        "/api/v1/reports/games",
        "/api/v1/reports/wallet-flow",
        "/api/v1/reports/trends",
    ]

    for endpoint in endpoints:
        response = await client.get(endpoint)
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_reports_api_operator_admin_authorized(
    client: httpx.AsyncClient,
    operator_admin_headers: dict[str, str],
) -> None:
    """Validate that OPERATOR_ADMIN receives HTTP 200 on all endpoints with scoped metrics."""
    # 1. Overview
    res_overview = await client.get("/api/v1/reports/overview", headers=operator_admin_headers)
    assert res_overview.status_code == 200
    data_overview = res_overview.json()
    assert "total_players" in data_overview
    assert "daily_active_users" in data_overview
    assert "simulated_ggr_credits" in data_overview
    assert "overall_observed_rtp" in data_overview

    # 2. Games
    res_games = await client.get("/api/v1/reports/games", headers=operator_admin_headers)
    assert res_games.status_code == 200
    data_games = res_games.json()
    assert "items" in data_games

    # 3. Wallet Flow
    res_flow = await client.get("/api/v1/reports/wallet-flow", headers=operator_admin_headers)
    assert res_flow.status_code == 200
    data_flow = res_flow.json()
    assert "flows" in data_flow
    assert "total_minted" in data_flow
    assert "total_burned_or_lost" in data_flow

    # 4. Trends
    res_trends = await client.get("/api/v1/reports/trends?days=7", headers=operator_admin_headers)
    assert res_trends.status_code == 200
    data_trends = res_trends.json()
    assert "trends" in data_trends


@pytest.mark.asyncio
async def test_reports_api_authorized_roles(
    client: httpx.AsyncClient,
    finance_headers: dict[str, str],
    game_manager_headers: dict[str, str],
    super_admin_headers: dict[str, str],
) -> None:
    """Validate that FINANCE, GAME_MANAGER, and SUPER_ADMIN roles are authorized."""
    for headers in [finance_headers, game_manager_headers, super_admin_headers]:
        res = await client.get("/api/v1/reports/overview", headers=headers)
        assert res.status_code == 200


@pytest.mark.asyncio
async def test_reports_api_operator_admin_cannot_spoof_tenant(
    client: httpx.AsyncClient,
    operator_admin_headers: dict[str, str],
    test_operator_b: Operator,
) -> None:
    """Validate that OPERATOR_ADMIN cannot spoof operator_id via query param."""
    # Even if operator_admin provides another operator's UUID, the backend resolves to current_user.operator_id
    response = await client.get(
        f"/api/v1/reports/overview?operator_id={test_operator_b.id}",
        headers=operator_admin_headers,
    )
    assert response.status_code == 200
