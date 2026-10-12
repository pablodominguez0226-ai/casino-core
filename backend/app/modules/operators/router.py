import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.tenant.context import get_optional_tenant_id
from app.modules.identity.dependencies import (
    get_optional_current_user,
    require_permission,
)
from app.modules.identity.models import User
from app.modules.operators.schemas import (
    OperatorCatalogItemResponse,
    OperatorCreateRequest,
    OperatorGameConfigResponse,
    OperatorGameConfigUpdateRequest,
    OperatorResponse,
)
from app.modules.operators.services import (
    create_operator,
    get_operator_catalog,
    update_game_config,
)

router = APIRouter(prefix="/operators", tags=["operators"])
admin_router = APIRouter(prefix="/admin/operators", tags=["operators-admin"])


@admin_router.post(
    "",
    response_model=OperatorResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new B2B tenant operator",
)
@admin_router.post(
    "/",
    response_model=OperatorResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
async def register_operator(
    data: OperatorCreateRequest,
    current_user: User = Depends(require_permission("system:admin")),
    db: AsyncSession = Depends(get_db_session),
) -> OperatorResponse:
    """Create a new operator tenant. Restricted to SUPER_ADMIN."""
    operator = await create_operator(db, data)
    return OperatorResponse.model_validate(operator)


@router.get(
    "/catalog",
    response_model=list[OperatorCatalogItemResponse],
    summary="Get operator customized game catalog",
)
async def get_catalog(
    current_user: User | None = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> list[OperatorCatalogItemResponse]:
    """Retrieve catalog of games with tenant-specific overrides."""
    tenant_id = get_optional_tenant_id()
    if not tenant_id and current_user:
        tenant_id = current_user.operator_id
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant context required to access game catalog",
        )
    catalog = await get_operator_catalog(db, tenant_id)
    return [OperatorCatalogItemResponse.model_validate(item) for item in catalog]


@router.put(
    "/games/{game_id}/config",
    response_model=OperatorGameConfigResponse,
    summary="Configure operator-specific game limits and status",
)
async def update_game_configuration(
    game_id: uuid.UUID,
    data: OperatorGameConfigUpdateRequest,
    current_user: User = Depends(require_permission("games:manage")),
    db: AsyncSession = Depends(get_db_session),
) -> OperatorGameConfigResponse:
    """Update min/max bet and enabled status for a game under the active operator."""
    tenant_id = get_optional_tenant_id()
    if not tenant_id:
        tenant_id = current_user.operator_id
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant context required to update game config",
        )
    config = await update_game_config(db, tenant_id, game_id, data)
    return OperatorGameConfigResponse.model_validate(config)
