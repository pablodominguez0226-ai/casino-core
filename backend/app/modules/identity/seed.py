import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.identity.models import Permission, Role

logger = logging.getLogger(__name__)

DEFAULT_PERMISSIONS: list[dict[str, str]] = [
    {"code": "system:admin", "description": "Full system administrative access"},
    {"code": "operator:admin", "description": "Operator management access"},
    {"code": "users:read", "description": "Read user identity profile"},
    {"code": "users:write", "description": "Modify user identity and roles"},
    {"code": "gaming:spin", "description": "Execute casino game spins"},
    {"code": "gaming:play", "description": "Access game lobby and gameplay"},
    {"code": "audit:read", "description": "Read forensic audit logs"},
    {"code": "reports:read", "description": "Read operator reports and operational analytics"},
    {"code": "compliance:write", "description": "Review and update KYC and compliance cases"},
    {"code": "games:manage", "description": "Configure game catalog and bet limits"},
]

DEFAULT_ROLES: dict[str, dict[str, list[str] | str]] = {
    "SUPER_ADMIN": {
        "description": "Global platform administrator",
        "permissions": [
            "system:admin",
            "operator:admin",
            "users:read",
            "users:write",
            "gaming:spin",
            "gaming:play",
            "audit:read",
            "reports:read",
            "compliance:write",
            "games:manage",
        ],
    },
    "OPERATOR_ADMIN": {
        "description": "Tenant operator administrator",
        "permissions": [
            "operator:admin",
            "users:read",
            "users:write",
            "reports:read",
            "games:manage",
        ],
    },
    "PLAYER": {
        "description": "Standard casino player",
        "permissions": [
            "gaming:spin",
            "gaming:play",
        ],
    },
    "COMPLIANCE": {
        "description": "Compliance and forensic auditor",
        "permissions": [
            "audit:read",
            "users:read",
            "compliance:write",
        ],
    },
    "FINANCE": {
        "description": "Financial and ledger auditor",
        "permissions": [
            "reports:read",
            "users:read",
            "audit:read",
        ],
    },
    "GAME_MANAGER": {
        "description": "Game catalog and operations manager",
        "permissions": [
            "reports:read",
            "gaming:play",
            "games:manage",
        ],
    },
}


async def seed_identity_defaults(db: AsyncSession) -> None:
    """Idempotently seed default permissions and roles into the database."""
    # 1. Seed permissions
    perm_map: dict[str, Permission] = {}
    for p_info in DEFAULT_PERMISSIONS:
        stmt = select(Permission).where(Permission.code == p_info["code"])
        perm = await db.scalar(stmt)
        if not perm:
            perm = Permission(
                id=uuid.uuid4(),
                code=p_info["code"],
                description=p_info["description"],
            )
            db.add(perm)
            await db.flush()
        perm_map[p_info["code"]] = perm

    # 2. Seed roles and associate permissions
    for role_name, role_info in DEFAULT_ROLES.items():
        stmt = select(Role).where(Role.name == role_name).options(selectinload(Role.permissions))
        role = await db.scalar(stmt)
        desired_perm_codes = set(role_info["permissions"])
        if not role:
            role = Role(
                id=uuid.uuid4(),
                name=role_name,
                description=str(role_info["description"]),
                operator_id=None,
            )
            role.permissions = [perm_map[c] for c in desired_perm_codes if c in perm_map]
            db.add(role)
            await db.flush()
        else:
            existing_perm_codes = {p.code for p in role.permissions}
            for code in desired_perm_codes:
                if code not in existing_perm_codes and code in perm_map:
                    role.permissions.append(perm_map[code])

    await db.commit()
    logger.info("Default roles and permissions verified/seeded successfully.")
