"""Tests for Responsible Gaming limits enforcement and irrevocable self-exclusion.

Módulo educativo. Las verificaciones y límites son simulados y no reemplazan sistemas regulatorios reales.
"""
from datetime import timedelta
import uuid

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import utc_now
from app.modules.audit.models import AuditLogRecord
from app.modules.gaming.enums import GameSessionStatus
from app.modules.gaming.models import Game, GameSession
from app.modules.identity.models import User
from app.modules.responsible.services import ResponsibleGamingService
from app.modules.wallet.models import Wallet


@pytest.mark.asyncio
async def test_self_exclusion_blocks_spin_with_403_forbidden(
    client: httpx.AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    test_wallet: Wallet,
    test_game: Game,
    test_session: GameSession,
    auth_headers: dict[str, str],
) -> None:
    """Test de autoexclusión: activar exclusión por 30 días y verificar que /spin retorna 403 Forbidden.

    Módulo educativo. Las verificaciones y límites son simulados y no reemplazan sistemas regulatorios reales.
    """
    # 1. Apply 30 days self-exclusion via API
    resp_exclude = await client.post(
        "/api/v1/responsible/self-exclusion",
        headers=auth_headers,
        json={"duration_days": 30, "reason": "Taking a needed break"},
    )
    assert resp_exclude.status_code == 201
    exclude_data = resp_exclude.json()
    assert exclude_data["user_id"] == str(test_user.id)
    assert exclude_data["is_active"] is True

    # 2. Verify status endpoint confirms player is excluded
    resp_status = await client.get(
        "/api/v1/responsible/self-exclusion/status",
        headers=auth_headers,
    )
    assert resp_status.status_code == 200
    assert resp_status.json()["is_excluded"] is True

    # 3. Create a new active session or attempt to spin on the existing session
    # Notice that applying self-exclusion cancels active sessions.
    # If the user tries to spin, it MUST return 403 Forbidden because player is self-excluded!
    spin_payload = {"bet_amount": 10}
    idempotency_key = f"spin-{uuid.uuid4()}"

    resp_spin = await client.post(
        f"/api/v1/games/sessions/{test_session.id}/spin",
        headers={**auth_headers, "Idempotency-Key": idempotency_key},
        json=spin_payload,
    )
    assert resp_spin.status_code == 403, f"Expected 403 Forbidden but got {resp_spin.status_code}: {resp_spin.text}"
    error_data = resp_spin.json()
    assert "self-excluded" in error_data["detail"].lower()

    # 4. Also verify attempting to start a new game session returns 403 Forbidden
    resp_new_session = await client.post(
        "/api/v1/games/sessions",
        headers=auth_headers,
        json={"game_id": str(test_game.id)},
    )
    assert resp_new_session.status_code == 403
    assert "self-excluded" in resp_new_session.json()["detail"].lower()

    # 5. Verify audit log was recorded in audit_logs table
    stmt_audit = (
        select(AuditLogRecord)
        .where(
            AuditLogRecord.user_id == test_user.id,
            AuditLogRecord.action == "SELF_EXCLUSION_APPLIED",
        )
    )
    audit_entry = await db_session.scalar(stmt_audit)
    assert audit_entry is not None
    assert audit_entry.details["duration_days"] == 30


@pytest.mark.asyncio
async def test_daily_bet_limit_enforcement_aborts_spin_with_409_conflict(
    client: httpx.AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    test_wallet: Wallet,
    test_game: Game,
    test_session: GameSession,
    auth_headers: dict[str, str],
) -> None:
    """Test de límites diarios: configurar tope diario de 100 créditos, realizar apuestas que

    alcancen 100 créditos y verificar que una tirada subsiguiente por 10 créditos es rechazada con 409 Conflict.

    Módulo educativo. Las verificaciones y límites son simulados y no reemplazan sistemas regulatorios reales.
    """
    # 1. Configure daily_bet_limit of 100 credits via PUT /api/v1/responsible/limits
    resp_limits = await client.put(
        "/api/v1/responsible/limits",
        headers=auth_headers,
        json={"daily_bet_limit": 100},
    )
    assert resp_limits.status_code == 200
    limits_data = resp_limits.json()
    assert limits_data["daily_bet_limit"] == 100
    assert limits_data["user_id"] == str(test_user.id)

    # 2. Execute 2 spins of 50 credits each (total accumulated = 100 credits)
    for i in range(2):
        idem_key = f"spin-limit-{i}-{uuid.uuid4()}"
        resp_spin = await client.post(
            f"/api/v1/games/sessions/{test_session.id}/spin",
            headers={**auth_headers, "Idempotency-Key": idem_key},
            json={"bet_amount": 50},
        )
        assert resp_spin.status_code == 200, f"Spin {i+1} failed: {resp_spin.text}"

    # 3. Next spin of 10 credits: current_sum (100) + 10 = 110 > 100 -> Must be rejected with 409 Conflict
    idem_key_exceed = f"spin-limit-exceed-{uuid.uuid4()}"
    resp_exceed = await client.post(
        f"/api/v1/games/sessions/{test_session.id}/spin",
        headers={**auth_headers, "Idempotency-Key": idem_key_exceed},
        json={"bet_amount": 10},
    )
    assert resp_exceed.status_code == 409, f"Expected 409 Conflict, got {resp_exceed.status_code}: {resp_exceed.text}"
    detail = resp_exceed.json()["detail"].lower()
    assert "daily bet limit" in detail or "limit of 100 exceeded" in detail

    # 4. Verify player limits update generated an immutable audit log
    stmt_audit = (
        select(AuditLogRecord)
        .where(
            AuditLogRecord.user_id == test_user.id,
            AuditLogRecord.action == "PLAYER_LIMITS_UPDATED",
        )
    )
    audit_entry = await db_session.scalar(stmt_audit)
    assert audit_entry is not None
    assert audit_entry.details["daily_bet_limit"] == 100


@pytest.mark.asyncio
async def test_session_duration_limit_exceeded_raises_409(
    client: httpx.AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    test_wallet: Wallet,
    test_game: Game,
    test_session: GameSession,
    auth_headers: dict[str, str],
) -> None:
    """Validate that exceeding session_duration_minutes rejects gameplay with 409 Conflict."""
    # Configure session duration limit to 10 minutes
    await client.put(
        "/api/v1/responsible/limits",
        headers=auth_headers,
        json={"session_duration_minutes": 10},
    )

    # Artificially age the session start time to 15 minutes ago
    test_session.started_at = utc_now() - timedelta(minutes=15)
    await db_session.commit()

    # Attempt spin
    resp = await client.post(
        f"/api/v1/games/sessions/{test_session.id}/spin",
        headers={**auth_headers, "Idempotency-Key": f"duration-{uuid.uuid4()}"},
        json={"bet_amount": 10},
    )
    assert resp.status_code == 409
    assert "duration limit" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_self_exclusion_cancels_active_game_sessions(
    db_session: AsyncSession,
    test_user: User,
    test_session: GameSession,
) -> None:
    """Validate that applying self-exclusion cancels active game sessions in the database."""
    assert test_session.status == GameSessionStatus.ACTIVE

    exclusion = await ResponsibleGamingService.apply_self_exclusion(
        db=db_session,
        user_id=test_user.id,
        days=7,
        reason="Test self-exclusion cancellation",
    )
    assert exclusion.is_active is True

    await db_session.refresh(test_session)
    assert test_session.status == GameSessionStatus.CANCELLED
