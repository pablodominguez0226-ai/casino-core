import uuid

from fastapi import HTTPException, status

from app.core.tenant.context import get_optional_tenant_id


async def require_tenant_context() -> uuid.UUID:
    """FastAPI dependency ensuring the active tenant context is present and validated.

    Returns:
        uuid.UUID: The validated operator UUID for the current request.

    Raises:
        HTTPException: 400 Bad Request if no valid tenant context is present.
    """
    tenant_id = get_optional_tenant_id()
    if tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant context required for this operation",
        )
    return tenant_id
