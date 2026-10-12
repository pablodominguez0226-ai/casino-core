from datetime import timedelta
import logging

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import utc_now
from app.core.security import (
    create_access_token,
    generate_refresh_token_string,
    hash_password,
    hash_token,
    verify_password,
)
from app.modules.identity.models import PlayerProfile, RefreshToken, Role, User
from app.modules.identity.schemas import LoginRequest, UserRegisterRequest
from app.modules.operators.models import Operator

logger = logging.getLogger(__name__)


class AuthService:
    """Domain service handling authentication, registration, and token lifecycle."""

    @staticmethod
    async def register_player(db: AsyncSession, data: UserRegisterRequest) -> User:
        """Register a new player account scoped to a specific operator tenant."""
        # 1. Verify operator existence and active status
        stmt_operator = select(Operator).where(
            Operator.slug == data.operator_slug,
            Operator.is_active.is_(True),
        )
        operator = await db.scalar(stmt_operator)
        if not operator:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Operator '{data.operator_slug}' not found or inactive",
            )

        # 2. Check for duplicate email within the same operator tenant
        stmt_duplicate = select(User).where(
            User.operator_id == operator.id,
            User.email == data.email,
        )
        existing_user = await db.scalar(stmt_duplicate)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User with this email already exists for this operator",
            )

        # 3. Retrieve default 'PLAYER' role (or create if not present)
        stmt_role = select(Role).where(Role.name == "PLAYER")
        player_role = await db.scalar(stmt_role)
        if not player_role:
            player_role = Role(
                name="PLAYER",
                description="Default casino player role",
            )
            db.add(player_role)
            await db.flush()

        # 4. Create User entity with Argon2id hashed password
        hashed_pwd = hash_password(data.password)
        new_user = User(
            operator_id=operator.id,
            email=data.email,
            hashed_password=hashed_pwd,
            is_active=True,
            is_verified=False,
            roles=[player_role],
        )
        db.add(new_user)
        await db.flush()

        # 5. Create associated PlayerProfile
        profile = PlayerProfile(
            user_id=new_user.id,
            username=data.username,
            first_name=data.first_name,
            last_name=data.last_name,
            birth_date=data.birth_date,
        )
        db.add(profile)
        await db.commit()

        # 6. Return fully eager-loaded user entity
        stmt_load = (
            select(User)
            .where(User.id == new_user.id)
            .options(
                selectinload(User.roles).selectinload(Role.permissions),
                selectinload(User.profile),
            )
        )
        loaded_user = await db.scalar(stmt_load)
        return loaded_user or new_user

    @staticmethod
    async def authenticate_user(
        db: AsyncSession, data: LoginRequest
    ) -> tuple[User, str, str]:
        """Authenticate user credentials against a tenant and issue token pair."""
        # 1. Validate operator tenant
        stmt_operator = select(Operator).where(
            Operator.slug == data.operator_slug,
            Operator.is_active.is_(True),
        )
        operator = await db.scalar(stmt_operator)
        if not operator:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 2. Find user scoped to operator
        stmt_user = (
            select(User)
            .where(
                User.operator_id == operator.id,
                User.email == data.email,
            )
            .options(
                selectinload(User.roles).selectinload(Role.permissions),
                selectinload(User.profile),
            )
        )
        user = await db.scalar(stmt_user)

        # 3. Verify user status and password
        if not user or not user.is_active or not verify_password(data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 4. Generate JWT Access Token and persistent Refresh Token
        access_token = create_access_token(
            data={"sub": str(user.id), "operator_id": str(user.operator_id)}
        )
        plain_refresh_token = generate_refresh_token_string()
        token_hash = hash_token(plain_refresh_token)
        expires_at = utc_now() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        refresh_record = RefreshToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
            is_revoked=False,
        )
        db.add(refresh_record)
        await db.commit()

        return user, access_token, plain_refresh_token

    @staticmethod
    async def rotate_refresh_token(
        db: AsyncSession, refresh_token_plain: str
    ) -> tuple[str, str]:
        """Validate, revoke old refresh token and issue a newly rotated token pair."""
        token_hash = hash_token(refresh_token_plain)
        stmt_token = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        token_record = await db.scalar(stmt_token)

        if not token_record:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if token_record.is_revoked:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has been revoked",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if token_record.expires_at < utc_now():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Retrieve user and ensure active
        stmt_user = select(User).where(User.id == token_record.user_id)
        user = await db.scalar(stmt_user)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is inactive or disabled",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Revoke existing refresh token
        token_record.is_revoked = True

        # Issue newly rotated access token and refresh token
        new_access_token = create_access_token(
            data={"sub": str(user.id), "operator_id": str(user.operator_id)}
        )
        new_refresh_plain = generate_refresh_token_string()
        new_token_hash = hash_token(new_refresh_plain)
        new_expires_at = utc_now() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        new_refresh_record = RefreshToken(
            user_id=user.id,
            token_hash=new_token_hash,
            expires_at=new_expires_at,
            is_revoked=False,
        )
        db.add(new_refresh_record)
        await db.commit()

        return new_access_token, new_refresh_plain
