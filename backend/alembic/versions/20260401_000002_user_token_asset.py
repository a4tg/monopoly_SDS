"""Add user token asset

Revision ID: 20260401_000002
Revises: 20260401_000001
Create Date: 2026-04-01
"""

from alembic import op
import sqlalchemy as sa


revision = "20260401_000002"
down_revision = "20260401_000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("token_asset", sa.String(length=120), nullable=True))
    op.execute("UPDATE users SET token_asset = 'token-01.png' WHERE token_asset IS NULL")
    op.alter_column("users", "token_asset", existing_type=sa.String(length=120), nullable=False)


def downgrade() -> None:
    op.drop_column("users", "token_asset")
