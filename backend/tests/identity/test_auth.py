from datetime import timedelta
import uuid

import httpx
import jwt
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_access_token,
    generate_refresh_token_string,
    hash_password,
    hash_token,
    verify_password,
)
from app.modules.operators.models import Operator


# ==============================================================================
# 1. Cryptographic Helpers Unit Tests
# ==============================================================================

def test_argon2id_password_hashing() -> None:
    """Validate that hash_password produces valid Argon2id hash and verifies correctly."""
    plain = "SuperSecurePassword123!"
    hashed = hash_password(plain)

    assert hashed.startswith("$argon2id$")
    assert verify_password(plain, hashed) is True
    assert verify_password("WrongPassword123!", hashed) is False


def test_token_hashing_and_generation() -> None:
    """Validate token generator uniqueness and SHA-256 token hashing."""
    tok1 = generate_refresh_token_string()
    tok2 = generate_refresh_token_string()

    assert tok1 != tok2
    assert len(tok1) >= 48

    hash1 = hash_token(tok1)
    hash2 = hash_token(tok2)
    assert len(hash1) == 64
    assert len(hash2) == 64
    assert hash1 != hash2
    assert hash1 == hash_token(tok1)  # deterministic


def test_jwt_access_token_creation_and_expiration() -> None:
    """Validate JWT access token encoding, payload decoding, and expiration claim."""
    user_id = str(uuid.uuid4())
    token = create_access_token(
        data={"sub": user_id, "custom_claim": "value"},
        expires_delta=timedelta(minutes=5),
    )

    decoded = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    assert decoded["sub"] == user_id
    assert decoded["custom_claim"] == "value"
    assert "exp" in decoded


# ==============================================================================
# 2. Registration and Duplicate Handling Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_register_player_success(
    client: httpx.AsyncClient, test_operator: Operator
) -> None:
    """Validate successful player registration under an operator."""
    payload = {
        "email": "new_player@casino.com",
        "password": "ValidPassword123!",
        "operator_slug": test_operator.slug,
        "username": "luckyspinner",
    }
    response = await client.post("/api/v1/auth/register", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "new_player@casino.com"
    assert data["operator_id"] == str(test_operator.id)
    assert data["is_active"] is True
    assert "PLAYER" in data["roles"]
    assert "id" in data


@pytest.mark.asyncio
async def test_register_duplicate_email_same_operator_rejected(
    client: httpx.AsyncClient, test_operator: Operator
) -> None:
    """Validate that duplicate email within the same operator tenant is rejected with 409."""
    payload = {
        "email": "unique_player@casino.com",
        "password": "ValidPassword123!",
        "operator_slug": test_operator.slug,
        "username": "playerone",
    }
    # Initial registration
    res1 = await client.post("/api/v1/auth/register", json=payload)
    assert res1.status_code == 201

    # Duplicate registration attempt
    res2 = await client.post("/api/v1/auth/register", json=payload)
    assert res2.status_code == 409
    assert "already exists" in res2.json()["detail"]


@pytest.mark.asyncio
async def test_register_nonexistent_operator_rejected(
    client: httpx.AsyncClient,
) -> None:
    """Validate registration fails with 404 when operator slug does not exist."""
    payload = {
        "email": "lost_player@casino.com",
        "password": "ValidPassword123!",
        "operator_slug": "non-existent-operator-slug-999",
        "username": "lostone",
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 404


# ==============================================================================
# 3. Multitenancy Isolation Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_multitenancy_same_email_different_operators_allowed(
    client: httpx.AsyncClient,
    test_operator: Operator,
    test_operator_two: Operator,
) -> None:
    """Validate multitenant isolation: identical email is accepted across distinct operators."""
    shared_email = "shared_identity@casino.com"
    password = "SafePassword123!"

    # Register under Operator 1
    res1 = await client.post(
        "/api/v1/auth/register",
        json={
            "email": shared_email,
            "password": password,
            "operator_slug": test_operator.slug,
            "username": "player_op1",
        },
    )
    assert res1.status_code == 201
    user1 = res1.json()

    # Register under Operator 2
    res2 = await client.post(
        "/api/v1/auth/register",
        json={
            "email": shared_email,
            "password": password,
            "operator_slug": test_operator_two.slug,
            "username": "player_op2",
        },
    )
    assert res2.status_code == 201
    user2 = res2.json()

    # Verify distinct accounts under distinct operators
    assert user1["id"] != user2["id"]
    assert user1["operator_id"] == str(test_operator.id)
    assert user2["operator_id"] == str(test_operator_two.id)
    assert user1["email"] == user2["email"] == shared_email


# ==============================================================================
# 4. Authentication / Login Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_login_success(
    client: httpx.AsyncClient, test_operator: Operator
) -> None:
    """Validate successful login returns access_token and refresh_token."""
    email = "login_success@casino.com"
    password = "CorrectPassword123!"

    # Setup player
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "operator_slug": test_operator.slug,
            "username": "login_winner",
        },
    )

    # Login
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": password,
            "operator_slug": test_operator.slug,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_incorrect_password(
    client: httpx.AsyncClient, test_operator: Operator
) -> None:
    """Validate login with incorrect password returns 401."""
    email = "wrong_pass@casino.com"
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "RealPassword123!",
            "operator_slug": test_operator.slug,
            "username": "wrong_guy",
        },
    )

    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": "IncorrectPassword999!",
            "operator_slug": test_operator.slug,
        },
    )
    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["detail"]


@pytest.mark.asyncio
async def test_login_nonexistent_user_or_operator(
    client: httpx.AsyncClient, test_operator: Operator
) -> None:
    """Validate login with non-existent user or invalid operator returns 401."""
    res_user = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "ghost@casino.com",
            "password": "AnyPassword123!",
            "operator_slug": test_operator.slug,
        },
    )
    assert res_user.status_code == 401

    res_op = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "ghost@casino.com",
            "password": "AnyPassword123!",
            "operator_slug": "invalid-slug",
        },
    )
    assert res_op.status_code == 401


# ==============================================================================
# 5. Refresh Token Rotation and Revocation Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_refresh_token_rotation_and_revocation(
    client: httpx.AsyncClient, test_operator: Operator
) -> None:
    """Validate successful refresh rotation and immediate rejection of revoked token."""
    email = "rotate_test@casino.com"
    password = "RotatePassword123!"

    # 1. Register & login
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "operator_slug": test_operator.slug,
            "username": "rotateman",
        },
    )
    login_res = await client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": password,
            "operator_slug": test_operator.slug,
        },
    )
    initial_tokens = login_res.json()
    initial_refresh = initial_tokens["refresh_token"]

    # 2. Rotate refresh token
    refresh_res = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": initial_refresh},
    )
    assert refresh_res.status_code == 200
    rotated_tokens = refresh_res.json()
    assert "access_token" in rotated_tokens
    assert "refresh_token" in rotated_tokens
    assert rotated_tokens["refresh_token"] != initial_refresh

    # 3. Attempt reuse of revoked refresh token (must be rejected)
    reuse_res = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": initial_refresh},
    )
    assert reuse_res.status_code == 401
    assert "revoked" in reuse_res.json()["detail"].lower()

    # 4. Attempt with forged / invalid refresh token
    invalid_res = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "totally-bogus-refresh-token-string"},
    )
    assert invalid_res.status_code == 401


# ==============================================================================
# 6. Current User Profile Endpoint (/users/me)
# ==============================================================================

@pytest.mark.asyncio
async def test_get_current_user_profile(
    client: httpx.AsyncClient, test_operator: Operator
) -> None:
    """Validate /users/me endpoint returns profile when authenticated with access token."""
    email = "profile_user@casino.com"
    password = "ProfilePassword123!"

    await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "operator_slug": test_operator.slug,
            "username": "profileuser",
        },
    )
    login_res = await client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": password,
            "operator_slug": test_operator.slug,
        },
    )
    access_token = login_res.json()["access_token"]

    # Valid authenticated call
    me_res = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["email"] == email
    assert me_data["operator_id"] == str(test_operator.id)
    assert "PLAYER" in me_data["roles"]

    # Unauthenticated call
    no_auth_res = await client.get("/api/v1/users/me")
    assert no_auth_res.status_code == 401

    # Invalid token call
    bad_auth_res = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": "Bearer bad-token-format"},
    )
    assert bad_auth_res.status_code == 401


# ==============================================================================
# 7. AuthService Domain Service Unit Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_auth_service_direct_lifecycle(
    db_session: AsyncSession, test_operator: Operator
) -> None:
    """Validate AuthService domain methods directly with database session."""
    from datetime import datetime, timezone
    from fastapi import HTTPException
    from app.modules.identity.models import RefreshToken
    from app.modules.identity.schemas import LoginRequest, UserRegisterRequest
    from app.modules.identity.services import AuthService

    # 1. Register player
    reg_req = UserRegisterRequest(
        email="direct_service@casino.com",
        password="DirectServicePassword123!",
        operator_slug=test_operator.slug,
        username="directuser",
    )
    user = await AuthService.register_player(db_session, reg_req)
    assert user.email == "direct_service@casino.com"
    assert user.operator_id == test_operator.id
    assert any(r.name == "PLAYER" for r in user.roles)

    # 2. Duplicate registration raises 409
    with pytest.raises(HTTPException) as exc_409:
        await AuthService.register_player(db_session, reg_req)
    assert exc_409.value.status_code == 409

    # 3. Nonexistent operator raises 404
    bad_op_req = UserRegisterRequest(
        email="other@casino.com",
        password="DirectServicePassword123!",
        operator_slug="unknown-operator-xyz",
        username="otheruser",
    )
    with pytest.raises(HTTPException) as exc_404:
        await AuthService.register_player(db_session, bad_op_req)
    assert exc_404.value.status_code == 404

    # 4. Authenticate success
    login_req = LoginRequest(
        email="direct_service@casino.com",
        password="DirectServicePassword123!",
        operator_slug=test_operator.slug,
    )
    auth_user, access_tok, refresh_tok = await AuthService.authenticate_user(
        db_session, login_req
    )
    assert auth_user.id == user.id
    assert access_tok is not None
    assert refresh_tok is not None

    # 5. Authenticate failure wrong password
    bad_login_req = LoginRequest(
        email="direct_service@casino.com",
        password="WrongPassword999!",
        operator_slug=test_operator.slug,
    )
    with pytest.raises(HTTPException) as exc_401_pass:
        await AuthService.authenticate_user(db_session, bad_login_req)
    assert exc_401_pass.value.status_code == 401

    # 6. Authenticate failure wrong operator
    bad_op_login = LoginRequest(
        email="direct_service@casino.com",
        password="DirectServicePassword123!",
        operator_slug="nonexistent-operator",
    )
    with pytest.raises(HTTPException) as exc_401_op:
        await AuthService.authenticate_user(db_session, bad_op_login)
    assert exc_401_op.value.status_code == 401

    # 7. Rotate refresh token success
    new_acc, new_ref = await AuthService.rotate_refresh_token(db_session, refresh_tok)
    assert new_acc is not None
    assert new_ref is not None
    assert new_ref != refresh_tok

    # 8. Reuse of revoked token raises 401
    with pytest.raises(HTTPException) as exc_revoked:
        await AuthService.rotate_refresh_token(db_session, refresh_tok)
    assert exc_revoked.value.status_code == 401
    assert "revoked" in exc_revoked.value.detail.lower()

    # 9. Invalid token raises 401
    with pytest.raises(HTTPException) as exc_invalid:
        await AuthService.rotate_refresh_token(db_session, "nonexistent-refresh-token")
    assert exc_invalid.value.status_code == 401

    # 10. Expired token raises 401
    expired_tok_str = generate_refresh_token_string()
    expired_record = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(expired_tok_str),
        expires_at=datetime.now(timezone.utc) - timedelta(days=1),
        is_revoked=False,
    )
    db_session.add(expired_record)
    await db_session.commit()

    with pytest.raises(HTTPException) as exc_expired:
        await AuthService.rotate_refresh_token(db_session, expired_tok_str)
    assert exc_expired.value.status_code == 401
    assert "expired" in exc_expired.value.detail.lower()

