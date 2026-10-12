from collections.abc import AsyncGenerator
import inspect
import logging
import uuid

from fastapi import Request, Response
from fastapi.responses import JSONResponse
import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.core.config import settings
from app.core.database import AsyncSessionLocal, get_db_session
from app.core.tenant.context import reset_current_tenant_id, set_current_tenant_id
from app.modules.identity.models import User
from app.modules.operators.models import Operator

logger = logging.getLogger("app.tenant")


async def _resolve_db_session(app) -> AsyncGenerator[AsyncSession, None]:
    """Provide a database session honoring FastAPI dependency overrides if configured."""
    if get_db_session in app.dependency_overrides:
        override = app.dependency_overrides[get_db_session]
        if inspect.isasyncgenfunction(override):
            async for s in override():
                yield s
                break
            return
        elif inspect.iscoroutinefunction(override):
            s = await override()
            yield s
            return
        else:
            s = override()
            yield s
            return
    async with AsyncSessionLocal() as s:
        yield s


class TenantMiddleware(BaseHTTPMiddleware):
    """Asynchronous multi-tenant isolation middleware.

    1. Extracts X-Operator-Slug header on /api/v1/ routes (except /health).
    2. Validates operator existence and active status against the database.
    3. Prevents cross-tenant operations when authenticated via JWT.
    4. Sets ambient request tenant context via ContextVars.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path

        # 1. Skip non-API routes, OpenAPI schemas, and public health checks
        if not path.startswith("/api/v1") or "/health" in path:
            return await call_next(request)

        operator_slug_header = request.headers.get("X-Operator-Slug")
        auth_header = request.headers.get("Authorization")

        # 2. Extract JWT token claims if Authorization header is present
        token_operator_id: uuid.UUID | None = None
        token_user_id: uuid.UUID | None = None
        if auth_header and auth_header.strip().lower().startswith("bearer "):
            token = auth_header.split(" ", 1)[1].strip()
            try:
                payload = jwt.decode(
                    token,
                    settings.SECRET_KEY,
                    algorithms=[settings.ALGORITHM],
                )
                raw_op_id = payload.get("operator_id")
                if raw_op_id:
                    token_operator_id = uuid.UUID(str(raw_op_id))
                raw_sub = payload.get("sub")
                if raw_sub:
                    token_user_id = uuid.UUID(str(raw_sub))
            except Exception:
                # Do not reject here; let downstream get_current_user enforce 401 Unauthorized
                pass

        ctx_token = None

        try:
            # 3. Handle explicit X-Operator-Slug header if provided
            if operator_slug_header is not None:
                slug_clean = operator_slug_header.strip()
                if not slug_clean:
                    return JSONResponse(
                        status_code=404,
                        content={"detail": "Operator Not Found"},
                    )

                operator: Operator | None = None
                async for session in _resolve_db_session(request.app):
                    stmt = select(Operator).where(
                        Operator.slug == slug_clean,
                        Operator.is_active.is_(True),
                    )
                    operator = await session.scalar(stmt)
                    break

                if not operator:
                    return JSONResponse(
                        status_code=404,
                        content={"detail": "Operator Not Found"},
                    )

                # Cross-tenant check: if JWT has an operator_id that differs from the slug operator
                if token_operator_id is not None and token_operator_id != operator.id:
                    # Allow SUPER_ADMIN to perform cross-tenant operations
                    is_super_admin = False
                    if token_user_id:
                        async for session in _resolve_db_session(request.app):
                            stmt_user = select(User).where(User.id == token_user_id).options(selectinload(User.roles))
                            user = await session.scalar(stmt_user)
                            if user:
                                role_names = {r.name for r in user.roles}
                                if "SUPER_ADMIN" in role_names:
                                    is_super_admin = True
                            break

                    if not is_super_admin:
                        return JSONResponse(
                            status_code=403,
                            content={"detail": "Cross-tenant operation prohibited"},
                        )

                # Set verified operator context
                ctx_token = set_current_tenant_id(operator.id)
                request.state.tenant_id = operator.id
                request.state.operator = operator

            elif token_operator_id is not None:
                # Fallback: ambient tenant context populated directly from authenticated JWT
                ctx_token = set_current_tenant_id(token_operator_id)
                request.state.tenant_id = token_operator_id

            response = await call_next(request)
            return response

        finally:
            if ctx_token is not None:
                reset_current_tenant_id(ctx_token)
