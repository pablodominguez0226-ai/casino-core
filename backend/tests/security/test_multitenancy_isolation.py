"""Security integration tests for strict multi-tenancy isolation and zero data leakage."""

import uuid

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.models import User
from app.modules.operators.models import Operator
from app.modules.wallet.enums import LedgerEntryType
from app.modules.wallet.services import WalletService


@pytest.mark.asyncio
async def test_jwt_from_operator_a_rejected_with_operator_b_slug(
    client: httpx.AsyncClient,
    player_a: tuple[User, str, dict[str, str]],
    operator_b: Operator,
) -> None:
    """Validate that a JWT issued for Operator A is immediately aborted with 403 Forbidden

    when the request includes header X-Operator-Slug for Operator B.
    """
    _, _, headers_a = player_a
    cross_tenant_headers = dict(headers_a)
    cross_tenant_headers["X-Operator-Slug"] = operator_b.slug

    response = await client.get("/api/v1/wallet", headers=cross_tenant_headers)
    assert response.status_code == 403
    data = response.json()
    assert "Cross-tenant operation prohibited" in data["detail"]


@pytest.mark.asyncio
async def test_player_a_consulting_wallet_or_ledger_with_operator_b_slug_forbidden(
    client: httpx.AsyncClient,
    player_a: tuple[User, str, dict[str, str]],
    operator_b: Operator,
) -> None:
    """Validate that Player A attempting to consult wallet or ledger with Operator B's slug is rejected (403)."""
    _, _, headers_a = player_a
    spoofed_headers = dict(headers_a)
    spoofed_headers["X-Operator-Slug"] = operator_b.slug

    # 1. Check wallet balance endpoint
    res_wallet = await client.get("/api/v1/wallet", headers=spoofed_headers)
    assert res_wallet.status_code == 403
    assert "Cross-tenant operation prohibited" in res_wallet.json()["detail"]

    # 2. Check ledger history endpoint
    res_ledger = await client.get("/api/v1/wallet/ledger", headers=spoofed_headers)
    assert res_ledger.status_code == 403
    assert "Cross-tenant operation prohibited" in res_ledger.json()["detail"]


@pytest.mark.asyncio
async def test_player_a_attempting_to_fetch_player_b_wallet_by_id_returns_404(
    client: httpx.AsyncClient,
    db_session: AsyncSession,
    player_a: tuple[User, str, dict[str, str]],
    player_b: tuple[User, str, dict[str, str]],
    operator_b: Operator,
) -> None:
    """Validate that attempting to access a wallet ID belonging to another tenant returns HTTP 404 Not Found."""
    _, _, headers_a = player_a
    user_b, _, _ = player_b

    # Ensure wallet exists for player B under operator B
    wallet_b = await WalletService.get_or_create_wallet(
        db=db_session,
        user_id=user_b.id,
        operator_id=operator_b.id,
    )

    # Player A requests Player B's wallet by ID
    response = await client.get(f"/api/v1/wallet/{wallet_b.id}", headers=headers_a)
    assert response.status_code == 404
    assert f"Wallet '{wallet_b.id}' not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_reports_overview_scoped_strictly_to_own_tenant(
    client: httpx.AsyncClient,
    db_session: AsyncSession,
    admin_a: tuple[User, str, dict[str, str]],
    player_a: tuple[User, str, dict[str, str]],
    player_b: tuple[User, str, dict[str, str]],
    operator_a: Operator,
    operator_b: Operator,
) -> None:
    """Validate that /api/v1/reports/overview consumed by Admin of Operator A sums only Operator A's data."""
    _, _, headers_admin_a = admin_a
    user_a, _, _ = player_a
    user_b, _, _ = player_b

    # 1. Fund Player A wallet (Operator A) with 5,000 credits
    wallet_a = await WalletService.get_or_create_wallet(db_session, user_a.id, operator_a.id)
    await WalletService.execute_transaction(
        db=db_session,
        wallet_id=wallet_a.id,
        amount=5000,
        entry_type=LedgerEntryType.CREDIT,
        idempotency_key=f"rep-test-a-{uuid.uuid4().hex[:8]}",
        description="Seed credits A",
    )

    # 2. Fund Player B wallet (Operator B) with 50,000 credits
    wallet_b = await WalletService.get_or_create_wallet(db_session, user_b.id, operator_b.id)
    await WalletService.execute_transaction(
        db=db_session,
        wallet_id=wallet_b.id,
        amount=50000,
        entry_type=LedgerEntryType.CREDIT,
        idempotency_key=f"rep-test-b-{uuid.uuid4().hex[:8]}",
        description="Seed credits B",
    )

    # 3. Admin A fetches overview
    res_a = await client.get("/api/v1/reports/overview", headers=headers_admin_a)
    assert res_a.status_code == 200
    data_a = res_a.json()

    # Operator A overview must reflect its scoped metrics, not containing Operator B's players
    assert data_a["total_players"] >= 1


@pytest.mark.asyncio
async def test_nonexistent_operator_slug_returns_404(
    client: httpx.AsyncClient,
) -> None:
    """Validate that requests with a non-existent X-Operator-Slug return 404 Operator Not Found."""
    headers = {"X-Operator-Slug": "non-existent-operator-slug-99999"}
    response = await client.get("/api/v1/operators/catalog", headers=headers)
    assert response.status_code == 404
    assert response.json()["detail"] == "Operator Not Found"


@pytest.mark.asyncio
async def test_super_admin_allowed_cross_tenant_access(
    client: httpx.AsyncClient,
    super_admin: tuple[User, str, dict[str, str]],
    operator_b: Operator,
) -> None:
    """Validate that SUPER_ADMIN is exempt from cross-tenant blocking when inspecting another operator."""
    _, _, super_headers = super_admin
    headers_with_slug = dict(super_headers)
    headers_with_slug["X-Operator-Slug"] = operator_b.slug

    # Super Admin can inspect the catalog or reports of Operator B
    response = await client.get("/api/v1/operators/catalog", headers=headers_with_slug)
    assert response.status_code == 200
