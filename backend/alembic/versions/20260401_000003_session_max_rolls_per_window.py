"""Add max rolls per window to game sessions

Revision ID: 20260401_000003
Revises: 20260401_000002
Create Date: 2026-04-01
"""

from alembic import op
import sqlalchemy as sa


revision = "20260401_000003"
down_revision = "20260401_000002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("game_sessions", sa.Column("max_rolls_per_window", sa.Integer(), nullable=True))
    op.execute("UPDATE game_sessions SET max_rolls_per_window = 1 WHERE max_rolls_per_window IS NULL")
    op.alter_column("game_sessions", "max_rolls_per_window", existing_type=sa.Integer(), nullable=False)


def downgrade() -> None:
    op.drop_column("game_sessions", "max_rolls_per_window")
