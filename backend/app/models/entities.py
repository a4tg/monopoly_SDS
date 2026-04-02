from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import JSON, DateTime, Enum as SAEnum, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class UserRole(str, Enum):
    ADMIN = "admin"
    PLAYER = "player"


class SessionStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    CLOSED = "closed"


class CellStatus(str, Enum):
    ACTIVE = "active"
    DEPLETED = "depleted"


class NotificationType(str, Enum):
    MANUAL_ACCRUAL = "manual_accrual"


class BalanceSource(str, Enum):
    ADMIN_MANUAL = "admin_manual"
    CELL_PURCHASE = "cell_purchase"
    SECRET_SHOP_PURCHASE = "secret_shop_purchase"
    MARKET_TRADE = "market_trade"


class TradeOfferStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    CANCELED = "canceled"


class AuctionLotStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"
    CLOSED_NO_WINNER = "closed_no_winner"


def enum_values(enum_cls: type[Enum]) -> list[str]:
    return [item.value for item in enum_cls]


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str | None] = mapped_column(String(320), unique=True, index=True, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), unique=True, index=True, nullable=True)
    password: Mapped[str] = mapped_column(String(256))
    token_asset: Mapped[str] = mapped_column(String(120), default="token-01.png")
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole, values_callable=enum_values), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    token: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[User] = relationship()


class GameSession(Base):
    __tablename__ = "game_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    status: Mapped[SessionStatus] = mapped_column(
        SAEnum(SessionStatus, values_callable=enum_values), default=SessionStatus.DRAFT, index=True
    )
    board_size: Mapped[int] = mapped_column(Integer, default=40)
    max_rolls_per_window: Mapped[int] = mapped_column(Integer, default=1)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    roll_window_config: Mapped[list[dict]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Cell(Base):
    __tablename__ = "cells"
    __table_args__ = (UniqueConstraint("game_session_id", "cell_index", name="uq_cell_session_index"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    game_session_id: Mapped[int] = mapped_column(ForeignKey("game_sessions.id", ondelete="CASCADE"), index=True)
    cell_index: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(String(500), default="")
    price_points: Mapped[int] = mapped_column(Integer)
    reward_name: Mapped[str] = mapped_column(String(120))
    image_url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    stock: Mapped[int] = mapped_column(Integer)
    status: Mapped[CellStatus] = mapped_column(
        SAEnum(CellStatus, values_callable=enum_values), default=CellStatus.ACTIVE, index=True
    )

    game_session: Mapped[GameSession] = relationship()


class PlayerSessionState(Base):
    __tablename__ = "player_session_state"
    __table_args__ = (UniqueConstraint("user_id", "game_session_id", name="uq_player_session"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    game_session_id: Mapped[int] = mapped_column(ForeignKey("game_sessions.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
    rolls_in_window: Mapped[int] = mapped_column(Integer, default=0)
    last_roll_slot_key: Mapped[str | None] = mapped_column(String(32), nullable=True)
    last_roll_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class MoveEvent(Base):
    __tablename__ = "move_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    game_session_id: Mapped[int] = mapped_column(ForeignKey("game_sessions.id", ondelete="CASCADE"), index=True)
    dice_value: Mapped[int] = mapped_column(Integer)
    from_position: Mapped[int] = mapped_column(Integer)
    to_position: Mapped[int] = mapped_column(Integer)
    cell_id: Mapped[int | None] = mapped_column(ForeignKey("cells.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PlayerBalanceEvent(Base):
    __tablename__ = "player_balance_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    game_session_id: Mapped[int | None] = mapped_column(ForeignKey("game_sessions.id", ondelete="SET NULL"), nullable=True)
    source: Mapped[BalanceSource] = mapped_column(SAEnum(BalanceSource, values_callable=enum_values), index=True)
    amount: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class InventoryItem(Base):
    __tablename__ = "inventory_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    game_session_id: Mapped[int] = mapped_column(ForeignKey("game_sessions.id", ondelete="CASCADE"), index=True)
    source_cell_id: Mapped[int | None] = mapped_column(ForeignKey("cells.id", ondelete="SET NULL"), nullable=True)
    reward_name: Mapped[str] = mapped_column(String(120))
    paid_points: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SecretShopItem(Base):
    __tablename__ = "secret_shop_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    price_points: Mapped[int] = mapped_column(Integer)
    stock: Mapped[int] = mapped_column(Integer)
    is_active: Mapped[int] = mapped_column(Integer, default=1)


class SecretShopPurchase(Base):
    __tablename__ = "secret_shop_purchases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    secret_shop_item_id: Mapped[int] = mapped_column(ForeignKey("secret_shop_items.id", ondelete="CASCADE"), index=True)
    purchase_month: Mapped[str] = mapped_column(String(7), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PlayerNotification(Base):
    __tablename__ = "player_notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    type: Mapped[NotificationType] = mapped_column(
        SAEnum(NotificationType, values_callable=enum_values), index=True
    )
    title: Mapped[str] = mapped_column(String(120))
    body: Mapped[str] = mapped_column(String(255))
    is_read: Mapped[int] = mapped_column(Integer, default=0, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SessionParticipant(Base):
    __tablename__ = "session_participants"
    __table_args__ = (UniqueConstraint("game_session_id", "user_id", name="uq_session_participant"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    game_session_id: Mapped[int] = mapped_column(ForeignKey("game_sessions.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    assigned_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PlayerTradeOffer(Base):
    __tablename__ = "player_trade_offers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    game_session_id: Mapped[int] = mapped_column(ForeignKey("game_sessions.id", ondelete="CASCADE"), index=True)
    offered_item_id: Mapped[int] = mapped_column(ForeignKey("inventory_items.id", ondelete="CASCADE"), index=True)
    from_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    to_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    offer_points: Mapped[int] = mapped_column(Integer)
    status: Mapped[TradeOfferStatus] = mapped_column(
        SAEnum(TradeOfferStatus, values_callable=enum_values), default=TradeOfferStatus.PENDING, index=True
    )
    note: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AuctionLot(Base):
    __tablename__ = "auction_lots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    game_session_id: Mapped[int] = mapped_column(ForeignKey("game_sessions.id", ondelete="CASCADE"), index=True)
    inventory_item_id: Mapped[int] = mapped_column(ForeignKey("inventory_items.id", ondelete="CASCADE"), index=True)
    seller_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    status: Mapped[AuctionLotStatus] = mapped_column(
        SAEnum(AuctionLotStatus, values_callable=enum_values), default=AuctionLotStatus.OPEN, index=True
    )
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    winner_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    winning_bid_points: Mapped[int | None] = mapped_column(Integer, nullable=True)


class AuctionBid(Base):
    __tablename__ = "auction_bids"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    auction_lot_id: Mapped[int] = mapped_column(ForeignKey("auction_lots.id", ondelete="CASCADE"), index=True)
    bidder_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    bid_points: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class SessionActivityEvent(Base):
    __tablename__ = "session_activity_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    game_session_id: Mapped[int] = mapped_column(ForeignKey("game_sessions.id", ondelete="CASCADE"), index=True)
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(String(180))
    body: Mapped[str] = mapped_column(String(500))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
