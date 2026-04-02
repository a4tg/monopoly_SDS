"""Session schedule fields and participants mapping

Revision ID: 20260401_000004
Revises: 20260401_000003
Create Date: 2026-04-01
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260401_000004"
down_revision = "20260401_000003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "game_sessions",
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "game_sessions",
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "game_sessions",
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "session_participants",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("game_session_id", sa.Integer(), sa.ForeignKey("game_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("assigned_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("assigned_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("game_session_id", "user_id", name="uq_session_participant"),
    )
    op.create_index("ix_session_participants_game_session_id", "session_participants", ["game_session_id"], unique=False)
    op.create_index("ix_session_participants_user_id", "session_participants", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_session_participants_user_id", table_name="session_participants")
    op.drop_index("ix_session_participants_game_session_id", table_name="session_participants")
    op.drop_table("session_participants")
    op.drop_column("game_sessions", "ended_at")
    op.drop_column("game_sessions", "ends_at")
    op.drop_column("game_sessions", "starts_at")
