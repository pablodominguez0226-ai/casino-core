"""Forensic Audit API router."""
from datetime import datetime
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.modules.audit.schemas import PaginatedAuditLogs
from app.modules.audit.services import AuditService
from app.modules.identity.dependencies import get_current_user
from app.modules.identity.models import User

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get(
    "",
    response_model=PaginatedAuditLogs,
    summary="Get paginated forensic audit logs",
)
@router.get(
    "/",
    response_model=PaginatedAuditLogs,
    include_in_schema=False,
)
async def get_audit_logs(
    action: str | None = Query(None, description="Filter by event action (e.g. CREDIT, BET_SIMULATION)"),
    start_date: datetime | None = Query(None, description="Filter logs starting from this timestamp"),
    end_date: datetime | None = Query(None, description="Filter logs up to this timestamp"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> PaginatedAuditLogs:
    """Retrieve immutable forensic audit logs. Requires COMPLIANCE, SUPER_ADMIN role or audit:read permission."""
    role_names = {r.name for r in current_user.roles}
    perm_codes = {p.code for r in current_user.roles for p in r.permissions}

    if (
        "SUPER_ADMIN" not in role_names
        and "COMPLIANCE" not in role_names
        and "audit:read" not in perm_codes
        and "system:admin" not in perm_codes
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Insufficient permissions for audit logs",
        )

    # Tenant filtering: Super admin sees all, others scoped to their operator
    operator_id: uuid.UUID | None = None
    if "SUPER_ADMIN" not in role_names and "system:admin" not in perm_codes:
        operator_id = current_user.operator_id

    return await AuditService.get_audit_logs(
        db=db,
        operator_id=operator_id,
        action=action,
        start_date=start_date,
        end_date=end_date,
        page=page,
        size=size,
    )
