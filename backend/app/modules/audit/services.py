"""Forensic Audit Service.

Queries ledger and gameplay history to provide immutable audit trails.
"""
from datetime import datetime
from typing import Any
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import utc_now
from app.modules.audit.models import AuditLogRecord
from app.modules.audit.schemas import AuditLog, PaginatedAuditLogs
from app.modules.wallet.models import LedgerEntry, Wallet


class AuditService:
    """Service providing forensic audit inspection across financial and gaming operations."""

    @staticmethod
    async def get_audit_logs(
        db: AsyncSession,
        operator_id: uuid.UUID | None = None,
        action: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        page: int = 1,
        size: int = 20,
    ) -> PaginatedAuditLogs:
        """Retrieve paginated forensic audit records filtered by action and date range."""
        query = (
            select(LedgerEntry)
            .join(Wallet, LedgerEntry.wallet_id == Wallet.id)
            .options(selectinload(LedgerEntry.wallet))
        )

        count_query = (
            select(func.count(LedgerEntry.id))
            .join(Wallet, LedgerEntry.wallet_id == Wallet.id)
        )

        if operator_id:
            query = query.where(Wallet.operator_id == operator_id)
            count_query = count_query.where(Wallet.operator_id == operator_id)

        if action:
            query = query.where(func.lower(LedgerEntry.entry_type) == action.lower())
            count_query = count_query.where(func.lower(LedgerEntry.entry_type) == action.lower())

        if start_date:
            query = query.where(LedgerEntry.created_at >= start_date)
            count_query = count_query.where(LedgerEntry.created_at >= start_date)

        if end_date:
            query = query.where(LedgerEntry.created_at <= end_date)
            count_query = count_query.where(LedgerEntry.created_at <= end_date)

        total = await db.scalar(count_query) or 0

        offset = (page - 1) * size
        query = query.order_by(LedgerEntry.created_at.desc()).offset(offset).limit(size)
        entries = (await db.scalars(query)).all()

        items: list[AuditLog] = []
        for entry in entries:
            items.append(
                AuditLog(
                    id=entry.id,
                    user_id=entry.wallet.user_id if entry.wallet else None,
                    operator_id=entry.wallet.operator_id if entry.wallet else None,
                    action=str(entry.entry_type.value if hasattr(entry.entry_type, "value") else entry.entry_type),
                    resource_type="WALLET_LEDGER",
                    resource_id=entry.id,
                    details={
                        "amount": entry.amount,
                        "balance_before": entry.balance_before,
                        "balance_after": entry.balance_after,
                        "description": entry.description,
                        "idempotency_key": entry.idempotency_key,
                        "reference_id": str(entry.reference_id) if entry.reference_id else None,
                    },
                    ip_address="127.0.0.1",
                    created_at=entry.created_at,
                )
            )

        return PaginatedAuditLogs(
            items=items,
            total=total,
            page=page,
            size=size,
        )

    @staticmethod
    async def log_event(
        db: AsyncSession,
        action: str,
        resource_type: str,
        resource_id: uuid.UUID | str | None = None,
        user_id: uuid.UUID | None = None,
        operator_id: uuid.UUID | None = None,
        details: dict[str, Any] | None = None,
        ip_address: str | None = None,
    ) -> AuditLogRecord:
        """Persist an immutable audit log record to audit_logs."""
        entry = AuditLogRecord(
            id=uuid.uuid4(),
            user_id=user_id,
            operator_id=operator_id,
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id is not None else None,
            details=details or {},
            ip_address=ip_address or "127.0.0.1",
            created_at=utc_now(),
        )
        db.add(entry)
        await db.flush()
        return entry

