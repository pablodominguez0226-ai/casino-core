"""seed_european_roulette_game

Revision ID: ce38711dd63e
Revises: 960805764696
Create Date: 2026-10-08 00:45:42.524273

Simulación educativa. RNG no apto ni certificado para juego con dinero real.
"""
from datetime import datetime, timezone
import json
from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ce38711dd63e'
down_revision: Union[str, None] = '960805764696'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    operators_res = bind.execute(sa.text("SELECT id FROM operators"))
    now = datetime.now(timezone.utc)
    config_json = json.dumps({
        "wheel": "EUROPEAN_SINGLE_ZERO",
        "pockets": 37,
        "disclaimer": "Simulación de Ruleta Europea para fines educativos. RNG no certificado para apuestas reales.",
    })
    for row in operators_res:
        op_id = row[0]
        existing = bind.execute(
            sa.text("SELECT 1 FROM games WHERE operator_id = :op_id AND code = 'EUROPEAN_ROULETTE_STD'"),
            {"op_id": op_id},
        ).fetchone()
        if not existing:
            bind.execute(
                sa.text(
                    """
                    INSERT INTO games (id, operator_id, code, name, game_type, min_bet, max_bet, config, is_active, created_at, updated_at)
                    VALUES (:id, :operator_id, :code, :name, 'ROULETTE', :min_bet, :max_bet, CAST(:config AS jsonb), true, :created_at, :updated_at)
                    """
                ),
                {
                    "id": uuid.uuid4(),
                    "operator_id": op_id,
                    "code": "EUROPEAN_ROULETTE_STD",
                    "name": "European Roulette Single Zero",
                    "min_bet": 5,
                    "max_bet": 5000,
                    "config": config_json,
                    "created_at": now,
                    "updated_at": now,
                },
            )


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text("DELETE FROM games WHERE code = 'EUROPEAN_ROULETTE_STD'"))
