"""Security integration tests for tenant-specific game overrides and custom catalogs."""

import uuid

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.gaming.enums import GameType
from app.modules.gaming.models import Game
from app.modules.gaming.services import GamingService
from app.modules.identity.models import User
from app.modules.operators.models import Operator
from app.modules.operators.schemas import OperatorGameConfigUpdateRequest
from app.modules.operators.services import OperatorService
from app.modules.wallet.enums import LedgerEntryType
from app.modules.wallet.services import WalletService


@pytest.fixture
async def shared_test_slot(db_session: AsyncSession, operator_a: Operator) -> Game:
    """Create a test slot game."""
    game = Game(
        id=uuid.uuid4(),
        operator_id=operator_a.id,
        code=f"SLOT_OVERRIDE_{uuid.uuid4().hex[:6]}",
        name="Multi-Tenant Mega Slot",
        game_type=GameType.SLOT,
        min_bet=10,
        max_bet=1000,
        is_active=True,
        config={"reels": 3, "rtp": 96.5},
    )
    db_session.add(game)
    await db_session.commit()
    await db_session.refresh(game)
    return game


@pytest.mark.asyncio
async def test_operator_bet_limit_overrides_differentiate_players(
    client: httpx.AsyncClient,
    db_session: AsyncSession,
    operator_a: Operator,
    operator_b: Operator,
    player_a: tuple[User, str, dict[str, str]],
    player_b: tuple[User, str, dict[str, str]],
    shared_test_slot: Game,
) -> None:
    """Validate that Operator A configures min_bet=50 and Operator B maintains min_bet=10.

    Player A betting 20 credits is rejected (400), while Player B betting 20 credits is accepted (200).
    Player A betting 50 credits is accepted (200).
    """
    user_a, _, headers_a = player_a
    user_b, _, headers_b = player_b

    # 1. Operator A sets min_bet = 50
    await OperatorService.update_game_config(
        db=db_session,
        operator_id=operator_a.id,
        game_id=shared_test_slot.id,
        data=OperatorGameConfigUpdateRequest(
            is_enabled=True,
            min_bet=50,
            max_bet=1000,
        ),
    )

    # 2. Operator B enables the game with default min_bet = 10
    await OperatorService.update_game_config(
        db=db_session,
        operator_id=operator_b.id,
        game_id=shared_test_slot.id,
        data=OperatorGameConfigUpdateRequest(
            is_enabled=True,
            min_bet=10,
            max_bet=1000,
        ),
    )

    # 3. Fund wallets for both players
    wallet_a = await WalletService.get_or_create_wallet(db_session, user_a.id, operator_a.id)
    await WalletService.execute_transaction(
        db=db_session,
        wallet_id=wallet_a.id,
        amount=10000,
        entry_type=LedgerEntryType.CREDIT,
        idempotency_key=f"fund-a-{uuid.uuid4().hex[:8]}",
        description="Initial balance A",
    )

    wallet_b = await WalletService.get_or_create_wallet(db_session, user_b.id, operator_b.id)
    await WalletService.execute_transaction(
        db=db_session,
        wallet_id=wallet_b.id,
        amount=10000,
        entry_type=LedgerEntryType.CREDIT,
        idempotency_key=f"fund-b-{uuid.uuid4().hex[:8]}",
        description="Initial balance B",
    )

    # 4. Start sessions for both players
    session_a = await GamingService.start_session(db_session, user_a.id, shared_test_slot.id)
    session_b = await GamingService.start_session(db_session, user_b.id, shared_test_slot.id)

    # 5. Player A attempts spin with 20 credits -> Must fail (min_bet is 50 for Operator A)
    res_a_20 = await client.post(
        f"/api/v1/games/sessions/{session_a.id}/spin",
        headers={**headers_a, "Idempotency-Key": f"spin-a-20-{uuid.uuid4().hex[:8]}"},
        json={"bet_amount": 20},
    )
    assert res_a_20.status_code in (400, 422), res_a_20.json()
    assert "outside allowed range [50, 1000]" in res_a_20.json()["detail"]

    # 6. Player B attempts spin with 20 credits -> Must succeed (min_bet is 10 for Operator B)
    res_b_20 = await client.post(
        f"/api/v1/games/sessions/{session_b.id}/spin",
        headers={**headers_b, "Idempotency-Key": f"spin-b-20-{uuid.uuid4().hex[:8]}"},
        json={"bet_amount": 20},
    )
    assert res_b_20.status_code == 200
    assert "round_id" in res_b_20.json()

    # 7. Player A attempts spin with 50 credits -> Must succeed
    res_a_50 = await client.post(
        f"/api/v1/games/sessions/{session_a.id}/spin",
        headers={**headers_a, "Idempotency-Key": f"spin-a-50-{uuid.uuid4().hex[:8]}"},
        json={"bet_amount": 50},
    )
    assert res_a_50.status_code == 200
    assert "round_id" in res_a_50.json()


@pytest.mark.asyncio
async def test_operator_admin_can_update_game_config_via_api(
    client: httpx.AsyncClient,
    admin_a: tuple[User, str, dict[str, str]],
    operator_a: Operator,
    shared_test_slot: Game,
) -> None:
    """Validate PUT /api/v1/operators/games/{game_id}/config modifies limits with games:manage permission."""
    _, _, admin_headers = admin_a

    payload = {
        "is_enabled": True,
        "min_bet": 100,
        "max_bet": 5000,
    }
    response = await client.put(
        f"/api/v1/operators/games/{shared_test_slot.id}/config",
        headers={**admin_headers, "X-Operator-Slug": operator_a.slug},
        json=payload,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["min_bet"] == 100
    assert data["max_bet"] == 5000
    assert data["is_enabled"] is True
    assert data["game_id"] == str(shared_test_slot.id)


@pytest.mark.asyncio
async def test_operator_catalog_endpoint_reflects_overrides(
    client: httpx.AsyncClient,
    db_session: AsyncSession,
    operator_a: Operator,
    player_a: tuple[User, str, dict[str, str]],
    shared_test_slot: Game,
) -> None:
    """Validate GET /api/v1/operators/catalog returns customized limits."""
    _, _, headers_a = player_a

    # Set custom override
    await OperatorService.update_game_config(
        db=db_session,
        operator_id=operator_a.id,
        game_id=shared_test_slot.id,
        data=OperatorGameConfigUpdateRequest(
            is_enabled=True,
            min_bet=75,
            max_bet=2500,
        ),
    )

    response = await client.get(
        "/api/v1/operators/catalog",
        headers={**headers_a, "X-Operator-Slug": operator_a.slug},
    )
    assert response.status_code == 200
    items = response.json()
    matched = [item for item in items if item["id"] == str(shared_test_slot.id)]
    assert len(matched) == 1
    assert matched[0]["min_bet"] == 75
    assert matched[0]["max_bet"] == 2500


@pytest.mark.asyncio
async def test_disabling_game_for_operator_blocks_session_creation(
    client: httpx.AsyncClient,
    db_session: AsyncSession,
    operator_a: Operator,
    player_a: tuple[User, str, dict[str, str]],
    shared_test_slot: Game,
) -> None:
    """Validate that when a game is disabled for an operator via OperatorGameConfig, new sessions are rejected with 404."""
    user_a, _, _ = player_a

    # Disable game for Operator A
    await OperatorService.update_game_config(
        db=db_session,
        operator_id=operator_a.id,
        game_id=shared_test_slot.id,
        data=OperatorGameConfigUpdateRequest(
            is_enabled=False,
            min_bet=10,
            max_bet=1000,
        ),
    )

    # Attempt to start session
    with pytest.raises(Exception) as exc_info:
        await GamingService.start_session(db_session, user_a.id, shared_test_slot.id)
    assert "not found or inactive" in str(exc_info.value)
