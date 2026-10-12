"""Tests for Simulated KYC workflow and Compliance RBAC review.

Módulo educativo. Las verificaciones y límites son simulados y no reemplazan sistemas regulatorios reales.
"""

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.models import AuditLogRecord
from app.modules.identity.models import User
from app.modules.responsible.enums import DocumentType, KycStatus


@pytest.mark.asyncio
async def test_kyc_submission_pending_status(
    client: httpx.AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test de subida de expediente KYC (PENDING).

    Módulo educativo. Las verificaciones y límites son simulados y no reemplazan sistemas regulatorios reales.
    """
    submit_payload = {
        "document_type": DocumentType.DNI.value,
        "document_number": "12345678A",
    }

    # 1. Submit KYC
    response = await client.post(
        "/api/v1/responsible/kyc/submit",
        headers=auth_headers,
        json=submit_payload,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["user_id"] == str(test_user.id)
    assert data["document_type"] == DocumentType.DNI.value
    assert data["document_number"] == "12345678A"
    assert data["status"] == KycStatus.PENDING.value
    assert data["rejection_reason"] is None

    # 2. Query own KYC status
    status_resp = await client.get(
        "/api/v1/responsible/kyc/status",
        headers=auth_headers,
    )
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] == KycStatus.PENDING.value

    # 3. Verify audit log entry for submission
    stmt_audit = (
        select(AuditLogRecord)
        .where(
            AuditLogRecord.user_id == test_user.id,
            AuditLogRecord.action == "KYC_SUBMITTED",
        )
    )
    audit_entry = await db_session.scalar(stmt_audit)
    assert audit_entry is not None
    assert audit_entry.details["document_number"] == "12345678A"


@pytest.mark.asyncio
async def test_kyc_review_by_player_rejected_with_403_forbidden(
    client: httpx.AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test de revisión administrativa: un usuario PLAYER intentando aprobar un KYC recibe 403 Forbidden.

    Módulo educativo. Las verificaciones y límites son simulados y no reemplazan sistemas regulatorios reales.
    """
    # 1. Submit KYC as PLAYER
    submit_resp = await client.post(
        "/api/v1/responsible/kyc/submit",
        headers=auth_headers,
        json={"document_type": DocumentType.PASSPORT.value, "document_number": "P987654321"},
    )
    assert submit_resp.status_code == 201
    profile_id = submit_resp.json()["id"]

    # 2. Attempt to approve KYC using PLAYER credentials
    review_resp = await client.post(
        f"/api/v1/responsible/admin/kyc/{profile_id}/review",
        headers=auth_headers,
        json={"status": KycStatus.APPROVED.value},
    )
    assert review_resp.status_code == 403
    assert "forbidden" in review_resp.json()["detail"].lower() or "insufficient" in review_resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_kyc_review_by_compliance_approves_and_records_audit(
    client: httpx.AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    test_compliance_user: User,
    auth_headers: dict[str, str],
    compliance_auth_headers: dict[str, str],
) -> None:
    """Un usuario con rol COMPLIANCE aprueba exitosamente el KYC y el estado cambia a APPROVED registrando la auditoría.

    Módulo educativo. Las verificaciones y límites son simulados y no reemplazan sistemas regulatorios reales.
    """
    # 1. Player submits KYC
    submit_resp = await client.post(
        "/api/v1/responsible/kyc/submit",
        headers=auth_headers,
        json={"document_type": DocumentType.DRIVER_LICENSE.value, "document_number": "DL-5551234"},
    )
    assert submit_resp.status_code == 201
    profile_id = submit_resp.json()["id"]

    # 2. Compliance officer reviews and approves
    review_resp = await client.post(
        f"/api/v1/responsible/admin/kyc/{profile_id}/review",
        headers=compliance_auth_headers,
        json={"status": KycStatus.APPROVED.value},
    )
    assert review_resp.status_code == 200
    review_data = review_resp.json()
    assert review_data["id"] == profile_id
    assert review_data["status"] == KycStatus.APPROVED.value
    assert review_data["reviewed_at"] is not None

    # 3. Verify user status reflects APPROVED
    status_resp = await client.get(
        "/api/v1/responsible/kyc/status",
        headers=auth_headers,
    )
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] == KycStatus.APPROVED.value

    # 4. Verify audit log record exists for the approval event
    stmt_audit = (
        select(AuditLogRecord)
        .where(
            AuditLogRecord.user_id == test_user.id,
            AuditLogRecord.action == "KYC_APPROVED",
        )
    )
    audit_entry = await db_session.scalar(stmt_audit)
    assert audit_entry is not None
    assert audit_entry.details["status"] == KycStatus.APPROVED.value
    assert audit_entry.details["reviewed_by"] == str(test_compliance_user.id)


@pytest.mark.asyncio
async def test_kyc_review_by_compliance_rejects_with_reason(
    client: httpx.AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    test_compliance_user: User,
    auth_headers: dict[str, str],
    compliance_auth_headers: dict[str, str],
) -> None:
    """Compliance officer rejects KYC with a mandatory rejection reason."""
    # 1. Player submits KYC
    submit_resp = await client.post(
        "/api/v1/responsible/kyc/submit",
        headers=auth_headers,
        json={"document_type": DocumentType.DNI.value, "document_number": "DNI-EXPIRED"},
    )
    assert submit_resp.status_code == 201
    profile_id = submit_resp.json()["id"]

    # 2. Compliance officer reviews and rejects
    review_resp = await client.post(
        f"/api/v1/responsible/admin/kyc/{profile_id}/review",
        headers=compliance_auth_headers,
        json={
            "status": KycStatus.REJECTED.value,
            "rejection_reason": "Document has expired and cannot be verified",
        },
    )
    assert review_resp.status_code == 200
    review_data = review_resp.json()
    assert review_data["status"] == KycStatus.REJECTED.value
    assert review_data["rejection_reason"] == "Document has expired and cannot be verified"

    # 3. Verify audit log
    stmt_audit = (
        select(AuditLogRecord)
        .where(
            AuditLogRecord.user_id == test_user.id,
            AuditLogRecord.action == "KYC_REJECTED",
        )
    )
    audit_entry = await db_session.scalar(stmt_audit)
    assert audit_entry is not None
    assert "expired" in audit_entry.details["rejection_reason"].lower()


@pytest.mark.asyncio
async def test_kyc_status_not_found_returns_404(
    client: httpx.AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """When a user has never submitted KYC, status endpoint returns 404."""
    resp = await client.get(
        "/api/v1/responsible/kyc/status",
        headers=auth_headers,
    )
    assert resp.status_code == 404
