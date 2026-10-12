import uuid

from fastapi import HTTPException
import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import create_access_token, hash_password
from app.modules.identity.dependencies import require_permission
from app.modules.identity.models import Permission, Role, User
from app.modules.operators.models import Operator


@pytest.mark.asyncio
async def test_rbac_player_denied_admin_endpoint(
    client: httpx.AsyncClient, test_operator: Operator
) -> None:
    """Validate that a user with role PLAYER is forbidden (403) from accessing system:admin endpoint."""
    # 1. Register a standard player
    email = "standard_player@casino.com"
    password = "PlayerPassword123!"

    reg_res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "operator_slug": test_operator.slug,
            "username": "justaplayer",
        },
    )
    assert reg_res.status_code == 201

    # 2. Login to get player access token
    login_res = await client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": password,
            "operator_slug": test_operator.slug,
        },
    )
    assert login_res.status_code == 200
    access_token = login_res.json()["access_token"]

    # 3. Attempt access to system:admin restricted endpoint
    response = await client.get(
        "/api/v1/test/admin-only",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == 403
    assert "Forbidden: Insufficient permissions" in response.json()["detail"]


@pytest.mark.asyncio
async def test_rbac_admin_granted_access(
    client: httpx.AsyncClient, db_session: AsyncSession, test_operator: Operator
) -> None:
    """Validate that a user with SUPER_ADMIN role (possessing system:admin) is authorized (200)."""
    # 1. Fetch SUPER_ADMIN role
    stmt_role = (
        select(Role)
        .where(Role.name == "SUPER_ADMIN")
        .options(selectinload(Role.permissions))
    )
    admin_role = await db_session.scalar(stmt_role)
    assert admin_role is not None

    # 2. Create an admin user directly
    admin_user = User(
        operator_id=test_operator.id,
        email="super_admin@casino.com",
        hashed_password=hash_password("AdminSecurePassword123!"),
        is_active=True,
        roles=[admin_role],
    )
    db_session.add(admin_user)
    await db_session.commit()
    await db_session.refresh(admin_user)

    # 3. Generate access token for the admin user
    admin_token = create_access_token(
        data={"sub": str(admin_user.id), "operator_id": str(test_operator.id)}
    )

    # 4. Access system:admin restricted endpoint
    response = await client.get(
        "/api/v1/test/admin-only",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "authorized"


@pytest.mark.asyncio
async def test_require_permission_dependency_direct() -> None:
    """Direct unit test for require_permission dependency logic."""
    perm_spin = Permission(id=uuid.uuid4(), code="gaming:spin")
    perm_admin = Permission(id=uuid.uuid4(), code="system:admin")

    role_player = Role(id=uuid.uuid4(), name="PLAYER", permissions=[perm_spin])
    role_admin = Role(id=uuid.uuid4(), name="ADMIN", permissions=[perm_admin])

    player_user = User(
        id=uuid.uuid4(),
        operator_id=uuid.uuid4(),
        email="p@test.com",
        hashed_password="...",
        roles=[role_player],
    )

    admin_user = User(
        id=uuid.uuid4(),
        operator_id=uuid.uuid4(),
        email="a@test.com",
        hashed_password="...",
        roles=[role_admin],
    )

    checker_admin = require_permission("system:admin")

    # Player should raise 403
    with pytest.raises(HTTPException) as exc_info:
        await checker_admin(current_user=player_user)
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Forbidden: Insufficient permissions"

    # Admin should succeed and return user
    result_user = await checker_admin(current_user=admin_user)
    assert result_user == admin_user
