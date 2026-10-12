import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.telemetry.metrics import metrics_collector

from app.modules.wallet.enums import LedgerEntryType
from app.modules.wallet.exceptions import (
    DuplicateTransactionException,
    InsufficientFundsException,
    WalletLockedException,
    WalletNotFoundException,
)
from app.modules.wallet.models import IdempotencyRecord, LedgerEntry, Wallet
from app.modules.wallet.schemas import WalletReconciliationResponse

logger = logging.getLogger(__name__)


class WalletService:
    """Domain service managing transactional wallet operations with strict concurrency and idempotency."""

    @classmethod
    async def get_or_create_wallet(
        cls,
        db: AsyncSession,
        user_id: uuid.UUID,
        operator_id: uuid.UUID,
    ) -> Wallet:
        """Retrieve existing wallet for user, or atomically create one if it does not exist."""
        stmt = select(Wallet).where(Wallet.user_id == user_id)
        wallet = await db.scalar(stmt)
        if wallet:
            return wallet

        wallet = Wallet(
            user_id=user_id,
            operator_id=operator_id,
            balance=0,
            currency="CREDITS",
            is_locked=False,
        )
        db.add(wallet)
        try:
            await db.commit()
            await db.refresh(wallet)
            return wallet
        except Exception:
            await db.rollback()
            # Concurrent creation race resolution
            wallet = await db.scalar(stmt)
            if wallet:
                return wallet
            raise

    @classmethod
    async def get_wallet_by_id(
        cls,
        db: AsyncSession,
        wallet_id: uuid.UUID,
    ) -> Wallet:
        """Retrieve wallet entity by its primary key ID."""
        wallet = await db.get(Wallet, wallet_id)
        if not wallet:
            raise WalletNotFoundException(f"Wallet with id '{wallet_id}' not found")
        return wallet

    @classmethod
    async def execute_transaction(
        cls,
        db: AsyncSession,
        wallet_id: uuid.UUID,
        amount: int,
        entry_type: LedgerEntryType,
        idempotency_key: str | None = None,
        reference_id: uuid.UUID | None = None,
        description: str | None = None,
        commit: bool = True,
    ) -> LedgerEntry:
        """Execute a financial wallet balance mutation under strict row-level lock and idempotency control."""
        # 1. If idempotency_key is present, check existing record before lock acquisition
        if idempotency_key:
            stmt_rec = select(IdempotencyRecord).where(IdempotencyRecord.key == idempotency_key)
            existing_rec = await db.scalar(stmt_rec)
            if existing_rec:
                return await cls._resolve_idempotent_result(
                    db=db,
                    record=existing_rec,
                    wallet_id=wallet_id,
                    amount=amount,
                    entry_type=entry_type,
                )

        try:
            # 2. Acquire row-level exclusive lock on the wallet row
            stmt = (
                select(Wallet)
                .where(Wallet.id == wallet_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            wallet = await db.scalar(stmt)
            if not wallet:
                raise WalletNotFoundException(f"Wallet with id '{wallet_id}' not found")

            # 2b. Re-check idempotency under lock in case a concurrent request just committed
            if idempotency_key:
                stmt_rec = (
                    select(IdempotencyRecord)
                    .where(IdempotencyRecord.key == idempotency_key)
                    .execution_options(populate_existing=True)
                )
                existing_rec = await db.scalar(stmt_rec)
                if existing_rec:
                    return await cls._resolve_idempotent_result(
                        db=db,
                        record=existing_rec,
                        wallet_id=wallet_id,
                        amount=amount,
                        entry_type=entry_type,
                    )

            # 3. Validate wallet is not locked
            if wallet.is_locked:
                raise WalletLockedException(f"Wallet '{wallet_id}' is locked")

            # 4. Check funds if operation is a debit/bet
            is_debit = entry_type in {LedgerEntryType.DEBIT, LedgerEntryType.BET_SIMULATION}
            if is_debit and wallet.balance < amount:
                raise InsufficientFundsException(
                    f"Insufficient funds: current balance is {wallet.balance}, required {amount}"
                )

            # 5. Record balance_before
            balance_before = wallet.balance

            # 6. Calculate balance_after
            if is_debit:
                balance_after = balance_before - amount
            else:
                balance_after = balance_before + amount

            # 7. Mutate wallet balance
            wallet.balance = balance_after

            # 8. Create and insert LedgerEntry
            entry = LedgerEntry(
                wallet_id=wallet.id,
                entry_type=entry_type,
                amount=amount,
                balance_before=balance_before,
                balance_after=balance_after,
                idempotency_key=idempotency_key,
                reference_id=reference_id,
                description=description,
            )
            db.add(entry)

            # 9. If idempotency key provided, persist IdempotencyRecord
            if idempotency_key:
                idempotency_record = IdempotencyRecord(
                    key=idempotency_key,
                    wallet_id=wallet.id,
                    response_status=200,
                    response_payload={
                        "id": str(entry.id),
                        "wallet_id": str(wallet.id),
                        "entry_type": entry_type.value,
                        "amount": amount,
                        "balance_before": balance_before,
                        "balance_after": balance_after,
                        "idempotency_key": idempotency_key,
                        "reference_id": str(reference_id) if reference_id else None,
                        "description": description,
                    },
                )
                db.add(idempotency_record)

            if commit:
                # 10. Commit transaction and refresh entry
                await db.commit()
                await db.refresh(entry)
            else:
                await db.flush()

            # Record financial transaction in telemetry metrics
            metrics_collector.record_financial_transaction()
            return entry

        except Exception:
            await db.rollback()
            raise

    @classmethod
    async def _resolve_idempotent_result(
        cls,
        db: AsyncSession,
        record: IdempotencyRecord,
        wallet_id: uuid.UUID,
        amount: int,
        entry_type: LedgerEntryType,
    ) -> LedgerEntry:
        """Validate idempotency key payload consistency and return original LedgerEntry."""
        payload = record.response_payload
        payload_amount = payload.get("amount")
        payload_entry_type = payload.get("entry_type")

        if (
            str(record.wallet_id) != str(wallet_id)
            or payload_amount != amount
            or payload_entry_type != entry_type.value
        ):
            raise DuplicateTransactionException(
                f"Idempotency key '{record.key}' was already processed with different parameters"
            )

        stmt = (
            select(LedgerEntry)
            .where(LedgerEntry.idempotency_key == record.key)
            .execution_options(populate_existing=True)
        )
        entry = await db.scalar(stmt)
        if entry:
            return entry

        if "id" in payload:
            entry_id = uuid.UUID(payload["id"])
            entry = await db.get(LedgerEntry, entry_id)
            if entry:
                return entry

        raise DuplicateTransactionException(
            f"Idempotency record '{record.key}' exists but original ledger entry cannot be found"
        )

    @classmethod
    async def get_ledger_entries(
        cls,
        db: AsyncSession,
        wallet_id: uuid.UUID,
        skip: int = 0,
        limit: int = 50,
    ) -> list[LedgerEntry]:
        """Retrieve paginated ledger movements for a wallet in descending chronological order."""
        stmt = (
            select(LedgerEntry)
            .where(LedgerEntry.wallet_id == wallet_id)
            .order_by(LedgerEntry.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await db.scalars(stmt)
        return list(result.all())

    @classmethod
    async def reconcile_wallet(
        cls,
        db: AsyncSession,
        wallet_id: uuid.UUID,
    ) -> WalletReconciliationResponse:
        """Perform mathematical audit comparing cached wallet balance against ledger movements."""
        wallet = await cls.get_wallet_by_id(db, wallet_id)

        stmt = select(LedgerEntry).where(LedgerEntry.wallet_id == wallet_id)
        result = await db.scalars(stmt)
        entries = result.all()

        calculated_balance = sum(
            -e.amount if e.entry_type in {LedgerEntryType.DEBIT, LedgerEntryType.BET_SIMULATION} else e.amount
            for e in entries
        )

        is_consistent = (wallet.balance == calculated_balance)

        return WalletReconciliationResponse(
            wallet_id=wallet.id,
            cached_balance=wallet.balance,
            calculated_ledger_balance=calculated_balance,
            is_consistent=is_consistent,
        )
