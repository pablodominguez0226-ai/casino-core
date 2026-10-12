"""seed_classic_blackjack_game

Revision ID: b9e9bc38832d
Revises: ce38711dd63e
Create Date: 2026-10-08 01:14:08.368946

Simulación educativa. RNG no apto ni certificado para juego con dinero real.
"""
from datetime import datetime, timezone
import json
from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b9e9bc38832d'
down_revision: Union[str, None] = 'ce38711dd63e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    operators_res = bind.execute(sa.text("SELECT id FROM operators"))
    now = datetime.now(timezone.utc)
    config_json = json.dumps({
        "decks": 6,
        "dealer_stands_on": 17,
        "disclaimer": "Simulación de Blackjack Clásico con fines didácticos. Módulo no apto para operaciones con dinero real.",
    })
    for row in operators_res:
        op_id = row[0]
        existing = bind.execute(
            sa.text("SELECT 1 FROM games WHERE operator_id = :op_id AND code = 'CLASSIC_BLACKJACK_6D'"),
            {"op_id": op_id},
        ).fetchone()
        if not existing:
            bind.execute(
                sa.text(
                    """
                    INSERT INTO games (id, operator_id, code, name, game_type, min_bet, max_bet, config, is_active, created_at, updated_at)
                    VALUES (:id, :operator_id, :code, :name, 'BLACKJACK', :min_bet, :max_bet, CAST(:config AS jsonb), true, :created_at, :updated_at)
                    """
                ),
                {
                    "id": uuid.uuid4(),
                    "operator_id": op_id,
                    "code": "CLASSIC_BLACKJACK_6D",
                    "name": "Classic Blackjack 6-Deck",
                    "min_bet": 10,
                    "max_bet": 2000,
                    "config": config_json,
                    "created_at": now,
                    "updated_at": now,
                },
            )


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text("DELETE FROM games WHERE code = 'CLASSIC_BLACKJACK_6D'"))
