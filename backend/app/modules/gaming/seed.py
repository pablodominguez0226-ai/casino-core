"""Gaming initial seed data.

Simulación educativa. RNG no apto ni certificado para juego con dinero real.
"""
import logging
from typing import Any
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.gaming.enums import GameType, SlotSymbol
from app.modules.gaming.models import Game
from app.modules.operators.models import Operator

logger = logging.getLogger(__name__)

DEFAULT_GAME_CODE = "CLASSIC_FRUIT_SLOT"
DEFAULT_GAME_NAME = "Classic Fruit Slot"
DEFAULT_GAME_CONFIG: dict[str, Any] = {
    "reels": [
        [s.value for s in [SlotSymbol.CHERRY, SlotSymbol.LEMON, SlotSymbol.ORANGE, SlotSymbol.BELL, SlotSymbol.SEVEN]],
        [s.value for s in [SlotSymbol.CHERRY, SlotSymbol.LEMON, SlotSymbol.ORANGE, SlotSymbol.BELL, SlotSymbol.SEVEN]],
        [s.value for s in [SlotSymbol.CHERRY, SlotSymbol.LEMON, SlotSymbol.ORANGE, SlotSymbol.BELL, SlotSymbol.SEVEN]],
    ],
    "paytable": {
        SlotSymbol.SEVEN.value: 100,
        SlotSymbol.BELL.value: 25,
        SlotSymbol.ORANGE.value: 10,
        SlotSymbol.LEMON.value: 5,
        SlotSymbol.CHERRY.value: 2,
    },
}

ROULETTE_GAME_CODE = "EUROPEAN_ROULETTE_STD"
ROULETTE_GAME_NAME = "European Roulette Single Zero"
ROULETTE_GAME_CONFIG: dict[str, Any] = {
    "wheel": "EUROPEAN_SINGLE_ZERO",
    "pockets": 37,
    "disclaimer": "Simulación de Ruleta Europea para fines educativos. RNG no certificado para apuestas reales.",
}

BLACKJACK_GAME_CODE = "CLASSIC_BLACKJACK_6D"
BLACKJACK_GAME_NAME = "Classic Blackjack 6-Deck"
BLACKJACK_GAME_CONFIG: dict[str, Any] = {
    "decks": 6,
    "dealer_stands_on": 17,
    "disclaimer": "Simulación de Blackjack Clásico con fines didácticos. Módulo no apto para operaciones con dinero real.",
}


async def seed_default_games(db: AsyncSession, operator_id: uuid.UUID | None = None) -> list[Game]:
    """Idempotently seed the default games (SLOT and ROULETTE) for specified operator or all operators."""
    seeded_games: list[Game] = []

    if operator_id:
        operator_ids = [operator_id]
    else:
        stmt_ops = select(Operator.id)
        operator_ids = list((await db.scalars(stmt_ops)).all())

    for op_id in operator_ids:
        # 1. Classic Slot
        stmt_slot = select(Game).where(
            Game.operator_id == op_id,
            Game.code == DEFAULT_GAME_CODE,
        )
        slot_game = await db.scalar(stmt_slot)
        if not slot_game:
            slot_game = Game(
                id=uuid.uuid4(),
                operator_id=op_id,
                code=DEFAULT_GAME_CODE,
                name=DEFAULT_GAME_NAME,
                game_type=GameType.SLOT,
                min_bet=10,
                max_bet=1000,
                config=DEFAULT_GAME_CONFIG,
                is_active=True,
            )
            db.add(slot_game)
            seeded_games.append(slot_game)

        # 2. European Roulette Single Zero
        stmt_roulette = select(Game).where(
            Game.operator_id == op_id,
            Game.code == ROULETTE_GAME_CODE,
        )
        roulette_game = await db.scalar(stmt_roulette)
        if not roulette_game:
            roulette_game = Game(
                id=uuid.uuid4(),
                operator_id=op_id,
                code=ROULETTE_GAME_CODE,
                name=ROULETTE_GAME_NAME,
                game_type=GameType.ROULETTE,
                min_bet=5,
                max_bet=5000,
                config=ROULETTE_GAME_CONFIG,
                is_active=True,
            )
            db.add(roulette_game)
            seeded_games.append(roulette_game)

        # 3. Classic Blackjack 6-Deck
        stmt_blackjack = select(Game).where(
            Game.operator_id == op_id,
            Game.code == BLACKJACK_GAME_CODE,
        )
        blackjack_game = await db.scalar(stmt_blackjack)
        if not blackjack_game:
            blackjack_game = Game(
                id=uuid.uuid4(),
                operator_id=op_id,
                code=BLACKJACK_GAME_CODE,
                name=BLACKJACK_GAME_NAME,
                game_type=GameType.BLACKJACK,
                min_bet=10,
                max_bet=2000,
                config=BLACKJACK_GAME_CONFIG,
                is_active=True,
            )
            db.add(blackjack_game)
            seeded_games.append(blackjack_game)

    if seeded_games:
        await db.commit()
        for g in seeded_games:
            await db.refresh(g)
        logger.info("Default games seeded for operator(s): %d game(s).", len(seeded_games))

    return seeded_games
