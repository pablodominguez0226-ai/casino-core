import logging
import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.gaming.models import Game
from app.modules.operators.models import Operator, OperatorGameConfig
from app.modules.operators.schemas import (
    OperatorCreateRequest,
    OperatorGameConfigUpdateRequest,
)

logger = logging.getLogger(__name__)


class OperatorService:
    """Domain service managing B2B operators and their game catalog overrides."""

    @staticmethod
    async def create_operator(db: AsyncSession, data: OperatorCreateRequest) -> Operator:
        """Register a new B2B tenant operator in the platform."""
        stmt = select(Operator).where(Operator.slug == data.slug.strip())
        existing = await db.scalar(stmt)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Operator with slug '{data.slug}' already exists",
            )

        operator = Operator(
            name=data.name.strip(),
            slug=data.slug.strip(),
            is_active=True,
        )
        db.add(operator)
        await db.commit()
        await db.refresh(operator)
        logger.info("Created new tenant operator: %s (slug: %s)", operator.id, operator.slug)
        return operator

    @staticmethod
    async def update_game_config(
        db: AsyncSession,
        operator_id: uuid.UUID,
        game_id: uuid.UUID,
        data: OperatorGameConfigUpdateRequest,
    ) -> OperatorGameConfig:
        """Upsert operator specific game limits and availability flags."""
        operator = await db.get(Operator, operator_id)
        if not operator or not operator.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Operator '{operator_id}' not found or inactive",
            )

        game = await db.get(Game, game_id)
        if not game:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Game '{game_id}' not found",
            )

        stmt = select(OperatorGameConfig).where(
            OperatorGameConfig.operator_id == operator_id,
            OperatorGameConfig.game_id == game_id,
        )
        config = await db.scalar(stmt)

        if config:
            config.is_enabled = data.is_enabled
            config.min_bet = data.min_bet
            config.max_bet = data.max_bet
            if data.custom_config is not None:
                config.custom_config = data.custom_config
        else:
            config = OperatorGameConfig(
                operator_id=operator_id,
                game_id=game_id,
                is_enabled=data.is_enabled,
                min_bet=data.min_bet,
                max_bet=data.max_bet,
                custom_config=data.custom_config,
            )
            db.add(config)

        await db.commit()
        await db.refresh(config)
        logger.info(
            "Updated game config for operator %s, game %s: min_bet=%d, max_bet=%d, enabled=%s",
            operator_id,
            game_id,
            config.min_bet,
            config.max_bet,
            config.is_enabled,
        )
        return config

    @staticmethod
    async def get_operator_catalog(db: AsyncSession, operator_id: uuid.UUID) -> list[dict]:
        """Retrieve the catalog of available games tailored to the operator's customized limits."""
        operator = await db.get(Operator, operator_id)
        if not operator or not operator.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Operator '{operator_id}' not found or inactive",
            )

        stmt_games = select(Game).where(Game.is_active.is_(True)).order_by(Game.name.asc())
        all_games = list((await db.scalars(stmt_games)).all())

        stmt_configs = select(OperatorGameConfig).where(OperatorGameConfig.operator_id == operator_id)
        configs_map = {c.game_id: c for c in (await db.scalars(stmt_configs)).all()}

        catalog: list[dict] = []
        for game in all_games:
            if game.id in configs_map:
                override = configs_map[game.id]
                if not override.is_enabled:
                    continue
                catalog.append(
                    {
                        "id": game.id,
                        "code": game.code,
                        "name": game.name,
                        "game_type": game.game_type.value if hasattr(game.game_type, "value") else str(game.game_type),
                        "is_enabled": override.is_enabled,
                        "min_bet": override.min_bet,
                        "max_bet": override.max_bet,
                        "custom_config": override.custom_config or game.config,
                    }
                )
            elif game.operator_id == operator_id:
                catalog.append(
                    {
                        "id": game.id,
                        "code": game.code,
                        "name": game.name,
                        "game_type": game.game_type.value if hasattr(game.game_type, "value") else str(game.game_type),
                        "is_enabled": game.is_active,
                        "min_bet": game.min_bet,
                        "max_bet": game.max_bet,
                        "custom_config": game.config,
                    }
                )

        return catalog


# Standalone function wrappers as specified in prompt
async def create_operator(db: AsyncSession, data: OperatorCreateRequest) -> Operator:
    return await OperatorService.create_operator(db, data)


async def update_game_config(
    db: AsyncSession,
    operator_id: uuid.UUID,
    game_id: uuid.UUID,
    data: OperatorGameConfigUpdateRequest,
) -> OperatorGameConfig:
    return await OperatorService.update_game_config(db, operator_id, game_id, data)


async def get_operator_catalog(db: AsyncSession, operator_id: uuid.UUID) -> list[dict]:
    return await OperatorService.get_operator_catalog(db, operator_id)
