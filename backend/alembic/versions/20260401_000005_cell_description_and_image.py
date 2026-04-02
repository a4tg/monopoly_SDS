"""Add optional cell description and image

Revision ID: 20260401_000005
Revises: 20260401_000004
Create Date: 2026-04-01
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260401_000005"
down_revision = "20260401_000004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "cells",
        sa.Column("description", sa.String(length=500), nullable=False, server_default=""),
    )
    op.add_column(
        "cells",
        sa.Column("image_url", sa.String(length=2000), nullable=True),
    )
    op.alter_column("cells", "description", server_default=None)


def downgrade() -> None:
    op.drop_column("cells", "image_url")
    op.drop_column("cells", "description")
