import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.modules.identity.dependencies import get_current_user
from app.modules.identity.models import User
from app.modules.wallet.enums import LedgerEntryType
from app.modules.wallet.schemas import (
    FaucetRequest,
    LedgerEntryResponse,
    TransactionRequest,
    WalletReconciliationResponse,
    WalletResponse,
)
from app.modules.wallet.services import WalletService

router = APIRouter(prefix="/wallet", tags=["wallet"])


@router.get(
    "/",
    response_model=WalletResponse,
    summary="Get current user wallet information and balance",
)
@router.get(
    "",
    response_model=WalletResponse,
    include_in_schema=False,
)
async def get_wallet(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> WalletResponse:
    """Retrieve virtual wallet details and current balance for the authenticated user."""
    wallet = await WalletService.get_or_create_wallet(
        db=db,
        user_id=current_user.id,
        operator_id=current_user.operator_id,
    )
    return WalletResponse.model_validate(wallet)


@router.post(
    "/faucet",
    response_model=LedgerEntryResponse,
    status_code=status.HTTP_200_OK,
    summary="Educational virtual credits reload",
)
async def reload_faucet(
    data: FaucetRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> LedgerEntryResponse:
    """Reload virtual educational credits into the user's wallet with mandatory Idempotency-Key."""
    wallet = await WalletService.get_or_create_wallet(
        db=db,
        user_id=current_user.id,
        operator_id=current_user.operator_id,
    )
    entry = await WalletService.execute_transaction(
        db=db,
        wallet_id=wallet.id,
        amount=data.amount,
        entry_type=LedgerEntryType.CREDIT,
        idempotency_key=idempotency_key,
        description="Educational faucet credit recharge",
    )
    return LedgerEntryResponse.model_validate(entry)


@router.post(
    "/debit",
    response_model=LedgerEntryResponse,
    status_code=status.HTTP_200_OK,
    summary="Debit virtual credits from wallet",
)
async def debit_funds(
    data: TransactionRequest,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> LedgerEntryResponse:
    """Debit virtual credits from the authenticated user's wallet."""
    wallet = await WalletService.get_or_create_wallet(
        db=db,
        user_id=current_user.id,
        operator_id=current_user.operator_id,
    )
    entry = await WalletService.execute_transaction(
        db=db,
        wallet_id=wallet.id,
        amount=data.amount,
        entry_type=LedgerEntryType.DEBIT,
        idempotency_key=idempotency_key,
        reference_id=data.reference_id,
        description=data.description or "Debit transaction",
    )
    return LedgerEntryResponse.model_validate(entry)


@router.post(
    "/credit",
    response_model=LedgerEntryResponse,
    status_code=status.HTTP_200_OK,
    summary="Credit virtual credits into wallet",
)
async def credit_funds(
    data: TransactionRequest,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> LedgerEntryResponse:
    """Credit virtual credits into the authenticated user's wallet."""
    wallet = await WalletService.get_or_create_wallet(
        db=db,
        user_id=current_user.id,
        operator_id=current_user.operator_id,
    )
    entry = await WalletService.execute_transaction(
        db=db,
        wallet_id=wallet.id,
        amount=data.amount,
        entry_type=LedgerEntryType.CREDIT,
        idempotency_key=idempotency_key,
        reference_id=data.reference_id,
        description=data.description or "Credit transaction",
    )
    return LedgerEntryResponse.model_validate(entry)


@router.get(
    "/ledger",
    response_model=list[LedgerEntryResponse],
    summary="Get paginated ledger movements history",
)
async def get_ledger_history(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> list[LedgerEntryResponse]:
    """Retrieve immutable paginated ledger entries for the user's wallet."""
    wallet = await WalletService.get_or_create_wallet(
        db=db,
        user_id=current_user.id,
        operator_id=current_user.operator_id,
    )
    entries = await WalletService.get_ledger_entries(
        db=db,
        wallet_id=wallet.id,
        skip=skip,
        limit=limit,
    )
    return [LedgerEntryResponse.model_validate(entry) for entry in entries]


@router.get(
    "/reconcile",
    response_model=WalletReconciliationResponse,
    summary="Audit wallet balance against ledger entries",
)
async def reconcile_wallet(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> WalletReconciliationResponse:
    """Validate mathematical consistency between wallet cached balance and ledger history."""
    wallet = await WalletService.get_or_create_wallet(
        db=db,
        user_id=current_user.id,
        operator_id=current_user.operator_id,
    )
    return await WalletService.reconcile_wallet(db=db, wallet_id=wallet.id)


@router.get(
    "/{wallet_id}",
    response_model=WalletResponse,
    summary="Get wallet by ID with strict tenant boundary",
)
async def get_wallet_by_id_endpoint(
    wallet_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> WalletResponse:
    """Retrieve wallet by UUID ensuring strict tenant isolation (returns 404 on cross-tenant or unauthorized)."""
    user_roles = {r.name for r in current_user.roles}
    is_super = "SUPER_ADMIN" in user_roles
    wallet = await WalletService.get_wallet_by_id(db=db, wallet_id=wallet_id)
    if not is_super and wallet.operator_id != current_user.operator_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Wallet '{wallet_id}' not found",
        )
    if not is_super and wallet.user_id != current_user.id and "OPERATOR_ADMIN" not in user_roles and "FINANCE" not in user_roles:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Wallet '{wallet_id}' not found",
        )
    return WalletResponse.model_validate(wallet)
