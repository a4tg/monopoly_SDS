"""Initial schema

Revision ID: 20260401_000001
Revises:
Create Date: 2026-04-01
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20260401_000001"
down_revision = None
branch_labels = None
depends_on = None


user_role = postgresql.ENUM("admin", "player", name="userrole", create_type=False)
session_status = postgresql.ENUM("draft", "active", "closed", name="sessionstatus", create_type=False)
cell_status = postgresql.ENUM("active", "depleted", name="cellstatus", create_type=False)
notification_type = postgresql.ENUM("manual_accrual", name="notificationtype", create_type=False)
balance_source = postgresql.ENUM("admin_manual", "cell_purchase", "secret_shop_purchase", name="balancesource", create_type=False)


def upgrade() -> None:
    bind = op.get_bind()
    user_role.create(bind, checkfirst=True)
    session_status.create(bind, checkfirst=True)
    cell_status.create(bind, checkfirst=True)
    notification_type.create(bind, checkfirst=True)
    balance_source.create(bind, checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("password", sa.String(length=256), nullable=False),
        sa.Column("role", user_role, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_phone", "users", ["phone"], unique=True)
    op.create_index("ix_users_role", "users", ["role"], unique=False)

    op.create_table(
        "auth_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("token", sa.String(length=128), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_auth_sessions_token", "auth_sessions", ["token"], unique=True)
    op.create_index("ix_auth_sessions_user_id", "auth_sessions", ["user_id"], unique=False)

    op.create_table(
        "game_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("status", session_status, nullable=False),
        sa.Column("roll_window_config", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_game_sessions_status", "game_sessions", ["status"], unique=False)

    op.create_table(
        "cells",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("game_session_id", sa.Integer(), sa.ForeignKey("game_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("cell_index", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("price_points", sa.Integer(), nullable=False),
        sa.Column("reward_name", sa.String(length=120), nullable=False),
        sa.Column("stock", sa.Integer(), nullable=False),
        sa.Column("status", cell_status, nullable=False),
        sa.UniqueConstraint("game_session_id", "cell_index", name="uq_cell_session_index"),
    )
    op.create_index("ix_cells_game_session_id", "cells", ["game_session_id"], unique=False)
    op.create_index("ix_cells_status", "cells", ["status"], unique=False)

    op.create_table(
        "player_session_state",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("game_session_id", sa.Integer(), sa.ForeignKey("game_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("rolls_in_window", sa.Integer(), nullable=False),
        sa.Column("last_roll_slot_key", sa.String(length=32), nullable=True),
        sa.Column("last_roll_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("user_id", "game_session_id", name="uq_player_session"),
    )
    op.create_index("ix_player_session_state_user_id", "player_session_state", ["user_id"], unique=False)
    op.create_index("ix_player_session_state_game_session_id", "player_session_state", ["game_session_id"], unique=False)

    op.create_table(
        "move_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("game_session_id", sa.Integer(), sa.ForeignKey("game_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("dice_value", sa.Integer(), nullable=False),
        sa.Column("from_position", sa.Integer(), nullable=False),
        sa.Column("to_position", sa.Integer(), nullable=False),
        sa.Column("cell_id", sa.Integer(), sa.ForeignKey("cells.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_move_events_user_id", "move_events", ["user_id"], unique=False)
    op.create_index("ix_move_events_game_session_id", "move_events", ["game_session_id"], unique=False)

    op.create_table(
        "player_balance_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("game_session_id", sa.Integer(), sa.ForeignKey("game_sessions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("source", balance_source, nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_player_balance_events_user_id", "player_balance_events", ["user_id"], unique=False)
    op.create_index("ix_player_balance_events_source", "player_balance_events", ["source"], unique=False)

    op.create_table(
        "inventory_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("game_session_id", sa.Integer(), sa.ForeignKey("game_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_cell_id", sa.Integer(), sa.ForeignKey("cells.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reward_name", sa.String(length=120), nullable=False),
        sa.Column("paid_points", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_inventory_items_user_id", "inventory_items", ["user_id"], unique=False)
    op.create_index("ix_inventory_items_game_session_id", "inventory_items", ["game_session_id"], unique=False)

    op.create_table(
        "secret_shop_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("price_points", sa.Integer(), nullable=False),
        sa.Column("stock", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Integer(), nullable=False),
    )

    op.create_table(
        "secret_shop_purchases",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("secret_shop_item_id", sa.Integer(), sa.ForeignKey("secret_shop_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("purchase_month", sa.String(length=7), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_secret_shop_purchases_user_id", "secret_shop_purchases", ["user_id"], unique=False)
    op.create_index("ix_secret_shop_purchases_secret_shop_item_id", "secret_shop_purchases", ["secret_shop_item_id"], unique=False)
    op.create_index("ix_secret_shop_purchases_purchase_month", "secret_shop_purchases", ["purchase_month"], unique=False)

    op.create_table(
        "player_notifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", notification_type, nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("body", sa.String(length=255), nullable=False),
        sa.Column("is_read", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_player_notifications_user_id", "player_notifications", ["user_id"], unique=False)
    op.create_index("ix_player_notifications_type", "player_notifications", ["type"], unique=False)
    op.create_index("ix_player_notifications_is_read", "player_notifications", ["is_read"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_player_notifications_is_read", table_name="player_notifications")
    op.drop_index("ix_player_notifications_type", table_name="player_notifications")
    op.drop_index("ix_player_notifications_user_id", table_name="player_notifications")
    op.drop_table("player_notifications")

    op.drop_index("ix_secret_shop_purchases_purchase_month", table_name="secret_shop_purchases")
    op.drop_index("ix_secret_shop_purchases_secret_shop_item_id", table_name="secret_shop_purchases")
    op.drop_index("ix_secret_shop_purchases_user_id", table_name="secret_shop_purchases")
    op.drop_table("secret_shop_purchases")
    op.drop_table("secret_shop_items")

    op.drop_index("ix_inventory_items_game_session_id", table_name="inventory_items")
    op.drop_index("ix_inventory_items_user_id", table_name="inventory_items")
    op.drop_table("inventory_items")

    op.drop_index("ix_player_balance_events_source", table_name="player_balance_events")
    op.drop_index("ix_player_balance_events_user_id", table_name="player_balance_events")
    op.drop_table("player_balance_events")

    op.drop_index("ix_move_events_game_session_id", table_name="move_events")
    op.drop_index("ix_move_events_user_id", table_name="move_events")
    op.drop_table("move_events")

    op.drop_index("ix_player_session_state_game_session_id", table_name="player_session_state")
    op.drop_index("ix_player_session_state_user_id", table_name="player_session_state")
    op.drop_table("player_session_state")

    op.drop_index("ix_cells_status", table_name="cells")
    op.drop_index("ix_cells_game_session_id", table_name="cells")
    op.drop_table("cells")

    op.drop_index("ix_game_sessions_status", table_name="game_sessions")
    op.drop_table("game_sessions")

    op.drop_index("ix_auth_sessions_user_id", table_name="auth_sessions")
    op.drop_index("ix_auth_sessions_token", table_name="auth_sessions")
    op.drop_table("auth_sessions")

    op.drop_index("ix_users_role", table_name="users")
    op.drop_index("ix_users_phone", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")

    bind = op.get_bind()
    balance_source.drop(bind, checkfirst=True)
    notification_type.drop(bind, checkfirst=True)
    cell_status.drop(bind, checkfirst=True)
    session_status.drop(bind, checkfirst=True)
    user_role.drop(bind, checkfirst=True)
