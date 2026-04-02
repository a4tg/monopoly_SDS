"""Add auction marketplace and session activity feed

Revision ID: 20260401_000009
Revises: 20260401_000008
Create Date: 2026-04-01
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20260401_000009"
down_revision = "20260401_000008"
branch_labels = None
depends_on = None


auction_lot_status = postgresql.ENUM(
    "open",
    "closed",
    "closed_no_winner",
    name="auctionlotstatus",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    auction_lot_status.create(bind, checkfirst=True)

    op.create_table(
        "auction_lots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("game_session_id", sa.Integer(), sa.ForeignKey("game_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("inventory_item_id", sa.Integer(), sa.ForeignKey("inventory_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("seller_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", auction_lot_status, nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("winner_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("winning_bid_points", sa.Integer(), nullable=True),
    )
    op.create_index("ix_auction_lots_game_session_id", "auction_lots", ["game_session_id"], unique=False)
    op.create_index("ix_auction_lots_inventory_item_id", "auction_lots", ["inventory_item_id"], unique=False)
    op.create_index("ix_auction_lots_seller_user_id", "auction_lots", ["seller_user_id"], unique=False)
    op.create_index("ix_auction_lots_status", "auction_lots", ["status"], unique=False)
    op.create_index("ix_auction_lots_ends_at", "auction_lots", ["ends_at"], unique=False)

    op.create_table(
        "auction_bids",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("auction_lot_id", sa.Integer(), sa.ForeignKey("auction_lots.id", ondelete="CASCADE"), nullable=False),
        sa.Column("bidder_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("bid_points", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_auction_bids_auction_lot_id", "auction_bids", ["auction_lot_id"], unique=False)
    op.create_index("ix_auction_bids_bidder_user_id", "auction_bids", ["bidder_user_id"], unique=False)
    op.create_index("ix_auction_bids_created_at", "auction_bids", ["created_at"], unique=False)

    op.create_table(
        "session_activity_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("game_session_id", sa.Integer(), sa.ForeignKey("game_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("body", sa.String(length=500), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_session_activity_events_game_session_id", "session_activity_events", ["game_session_id"], unique=False)
    op.create_index("ix_session_activity_events_actor_user_id", "session_activity_events", ["actor_user_id"], unique=False)
    op.create_index("ix_session_activity_events_event_type", "session_activity_events", ["event_type"], unique=False)
    op.create_index("ix_session_activity_events_created_at", "session_activity_events", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_session_activity_events_created_at", table_name="session_activity_events")
    op.drop_index("ix_session_activity_events_event_type", table_name="session_activity_events")
    op.drop_index("ix_session_activity_events_actor_user_id", table_name="session_activity_events")
    op.drop_index("ix_session_activity_events_game_session_id", table_name="session_activity_events")
    op.drop_table("session_activity_events")

    op.drop_index("ix_auction_bids_created_at", table_name="auction_bids")
    op.drop_index("ix_auction_bids_bidder_user_id", table_name="auction_bids")
    op.drop_index("ix_auction_bids_auction_lot_id", table_name="auction_bids")
    op.drop_table("auction_bids")

    op.drop_index("ix_auction_lots_ends_at", table_name="auction_lots")
    op.drop_index("ix_auction_lots_status", table_name="auction_lots")
    op.drop_index("ix_auction_lots_seller_user_id", table_name="auction_lots")
    op.drop_index("ix_auction_lots_inventory_item_id", table_name="auction_lots")
    op.drop_index("ix_auction_lots_game_session_id", table_name="auction_lots")
    op.drop_table("auction_lots")

    bind = op.get_bind()
    auction_lot_status.drop(bind, checkfirst=True)
