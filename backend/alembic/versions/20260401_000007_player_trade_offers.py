"""Add player trade offers marketplace

Revision ID: 20260401_000007
Revises: 20260401_000006
Create Date: 2026-04-01
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20260401_000007"
down_revision = "20260401_000006"
branch_labels = None
depends_on = None


trade_offer_status = postgresql.ENUM(
    "pending",
    "accepted",
    "rejected",
    "canceled",
    name="tradeofferstatus",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    trade_offer_status.create(bind, checkfirst=True)
    op.execute("ALTER TYPE balancesource ADD VALUE IF NOT EXISTS 'market_trade'")

    op.create_table(
        "player_trade_offers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("game_session_id", sa.Integer(), sa.ForeignKey("game_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("offered_item_id", sa.Integer(), sa.ForeignKey("inventory_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("from_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("to_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("offer_points", sa.Integer(), nullable=False),
        sa.Column("status", trade_offer_status, nullable=False),
        sa.Column("note", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_player_trade_offers_game_session_id", "player_trade_offers", ["game_session_id"], unique=False)
    op.create_index("ix_player_trade_offers_offered_item_id", "player_trade_offers", ["offered_item_id"], unique=False)
    op.create_index("ix_player_trade_offers_from_user_id", "player_trade_offers", ["from_user_id"], unique=False)
    op.create_index("ix_player_trade_offers_to_user_id", "player_trade_offers", ["to_user_id"], unique=False)
    op.create_index("ix_player_trade_offers_status", "player_trade_offers", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_player_trade_offers_status", table_name="player_trade_offers")
    op.drop_index("ix_player_trade_offers_to_user_id", table_name="player_trade_offers")
    op.drop_index("ix_player_trade_offers_from_user_id", table_name="player_trade_offers")
    op.drop_index("ix_player_trade_offers_offered_item_id", table_name="player_trade_offers")
    op.drop_index("ix_player_trade_offers_game_session_id", table_name="player_trade_offers")
    op.drop_table("player_trade_offers")
    bind = op.get_bind()
    trade_offer_status.drop(bind, checkfirst=True)
