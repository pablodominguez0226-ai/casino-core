from contextvars import ContextVar, Token
import uuid

# Ambient context variable holding the tenant/operator UUID for the current async execution context
current_tenant_id: ContextVar[uuid.UUID | None] = ContextVar("current_tenant_id", default=None)


def get_current_tenant_id() -> uuid.UUID:
    """Retrieve the currently active tenant operator UUID.

    Raises:
        LookupError: If no tenant context is set for the current request context.
    """
    tenant_id = current_tenant_id.get()
    if tenant_id is None:
        raise LookupError("Tenant context is not set in the current execution context")
    return tenant_id


def get_optional_tenant_id() -> uuid.UUID | None:
    """Retrieve the current tenant operator UUID, or None if not set."""
    return current_tenant_id.get()


def set_current_tenant_id(tenant_id: uuid.UUID | None) -> Token[uuid.UUID | None]:
    """Set the active tenant operator UUID for the current async execution context."""
    return current_tenant_id.set(tenant_id)


def reset_current_tenant_id(token: Token[uuid.UUID | None]) -> None:
    """Reset the tenant context variable to its previous state using the provided token."""
    current_tenant_id.reset(token)
