from collections.abc import Callable
import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import get_db_session
from app.modules.identity.models import Role, User

# OAuth2 bearer token extractors
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
optional_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db_session),
) -> User:
    """Dependency decoding JWT bearer token and returning the current authenticated User."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        user_id_raw: str | None = payload.get("sub")
        if user_id_raw is None:
            raise credentials_exception
        user_id = uuid.UUID(user_id_raw)
    except (jwt.PyJWTError, ValueError):
        raise credentials_exception

    stmt = (
        select(User)
        .where(User.id == user_id)
        .options(
            selectinload(User.roles).selectinload(Role.permissions),
            selectinload(User.profile),
        )
    )
    user = await db.scalar(stmt)
    if user is None or not user.is_active:
        raise credentials_exception

    return user


async def get_optional_current_user(
    token: str | None = Depends(optional_oauth2_scheme),
    db: AsyncSession = Depends(get_db_session),
) -> User | None:
    """Dependency returning the authenticated user if valid token is provided, or None."""
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id_raw = payload.get("sub")
        if not user_id_raw:
            return None
        user_id = uuid.UUID(user_id_raw)
        stmt = (
            select(User)
            .where(User.id == user_id)
            .options(
                selectinload(User.roles).selectinload(Role.permissions),
                selectinload(User.profile),
            )
        )
        user = await db.scalar(stmt)
        if user and user.is_active:
            return user
    except Exception:
        pass
    return None


def require_permission(permission_code: str) -> Callable:
    """Dependency factory returning a validator that enforces a specific RBAC permission."""

    async def permission_checker(
        current_user: User = Depends(get_current_user),
    ) -> User:
        user_permissions: set[str] = {
            perm.code
            for role in current_user.roles
            for perm in role.permissions
        }
        user_roles: set[str] = {role.name for role in current_user.roles}

        # Allow if specific permission is present, or if user is SUPER_ADMIN / has system:admin
        if (
            permission_code not in user_permissions
            and "system:admin" not in user_permissions
            and "SUPER_ADMIN" not in user_roles
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: Insufficient permissions",
            )
        return current_user

    return permission_checker
