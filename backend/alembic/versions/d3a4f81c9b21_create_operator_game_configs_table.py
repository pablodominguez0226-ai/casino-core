"""create_operator_game_configs_table

Revision ID: d3a4f81c9b21
Revises: b9e9bc38832d
Create Date: 2026-10-08 01:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'd3a4f81c9b21'
down_revision: Union[str, None] = 'b9e9bc38832d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'operator_game_configs',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('operator_id', sa.Uuid(), nullable=False),
        sa.Column('game_id', sa.Uuid(), nullable=False),
        sa.Column('is_enabled', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('min_bet', sa.BigInteger(), nullable=False),
        sa.Column('max_bet', sa.BigInteger(), nullable=False),
        sa.Column('custom_config', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint('max_bet >= min_bet', name='chk_operator_game_max_bet_ge_min'),
        sa.CheckConstraint('min_bet > 0', name='chk_operator_game_min_bet_positive'),
        sa.ForeignKeyConstraint(['game_id'], ['games.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['operator_id'], ['operators.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('operator_id', 'game_id', name='uq_operator_game'),
    )
    op.create_index(op.f('ix_operator_game_configs_game_id'), 'operator_game_configs', ['game_id'], unique=False)
    op.create_index(op.f('ix_operator_game_configs_operator_id'), 'operator_game_configs', ['operator_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_operator_game_configs_operator_id'), table_name='operator_game_configs')
    op.drop_index(op.f('ix_operator_game_configs_game_id'), table_name='operator_game_configs')
    op.drop_table('operator_game_configs')
