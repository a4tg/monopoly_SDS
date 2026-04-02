from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.models import (
    AuctionBid,
    AuctionLot,
    AuctionLotStatus,
    BalanceSource,
    Cell,
    CellStatus,
    GameSession,
    InventoryItem,
    MoveEvent,
    PlayerTradeOffer,
    SessionActivityEvent,
    PlayerSessionState,
    SecretShopItem,
    SecretShopPurchase,
    SessionParticipant,
    SessionStatus,
    TradeOfferStatus,
    User,
    UserRole,
)
from app.schemas.game import (
    AuctionBidRequest,
    AuctionLotCreateRequest,
    CellPurchaseRequest,
    RollResponse,
    SecretShopPurchaseRequest,
    TradeOfferCreateRequest,
    TradeOfferRespondRequest,
)
from app.services.balance import add_balance_event, get_player_balance
from app.services.game_engine import roll_d6
from app.services.roll_window import get_current_roll_slot_key

router = APIRouter()


def _get_active_session(db: Session) -> GameSession:
    session = db.execute(select(GameSession).where(GameSession.status == SessionStatus.ACTIVE).order_by(GameSession.id.desc())).scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=400, detail="No active game session")
    return session


def _ensure_session_is_open(session: GameSession) -> None:
    now_utc = datetime.now(timezone.utc)
    if session.ended_at is not None:
        raise HTTPException(status_code=400, detail="Game session is ended")
    if session.starts_at and now_utc < session.starts_at:
        raise HTTPException(status_code=400, detail="Game session has not started yet")
    if session.ends_at and now_utc > session.ends_at:
        raise HTTPException(status_code=400, detail="Game session is over")


def _ensure_player_assigned(db: Session, game_session_id: int, user_id: int) -> None:
    # Backward compatibility: when assignment list is empty, any player can join.
    has_assignments = db.execute(
        select(exists().where(SessionParticipant.game_session_id == game_session_id))
    ).scalar_one()
    if not has_assignments:
        return

    is_assigned = db.execute(
        select(
            exists().where(
                SessionParticipant.game_session_id == game_session_id,
                SessionParticipant.user_id == user_id,
            )
        )
    ).scalar_one()
    if not is_assigned:
        raise HTTPException(status_code=403, detail="Player is not assigned to this game session")


def _get_or_create_player_state(db: Session, user_id: int, game_session_id: int) -> PlayerSessionState:
    state = db.execute(
        select(PlayerSessionState).where(
            PlayerSessionState.user_id == user_id,
            PlayerSessionState.game_session_id == game_session_id,
        )
    ).scalar_one_or_none()
    if state:
        return state

    state = PlayerSessionState(user_id=user_id, game_session_id=game_session_id, position=0, rolls_in_window=0)
    db.add(state)
    db.flush()
    return state


def _normalize_position(position: int, board_size: int) -> int:
    if board_size <= 0:
        return 0
    if position < 0:
        return 0
    return position % board_size


def _get_session_players(db: Session, session_id: int) -> list[User]:
    has_assignments = db.execute(select(exists().where(SessionParticipant.game_session_id == session_id))).scalar_one()
    if has_assignments:
        return db.execute(
            select(User)
            .join(SessionParticipant, SessionParticipant.user_id == User.id)
            .where(SessionParticipant.game_session_id == session_id, User.role == UserRole.PLAYER)
            .order_by(User.id.asc())
        ).scalars().all()
    return db.execute(select(User).where(User.role == UserRole.PLAYER).order_by(User.id.asc())).scalars().all()


def _user_identifier(user: User) -> str:
    return user.email or user.phone or f"user-{user.id}"


def _log_session_event(
    db: Session,
    game_session_id: int,
    event_type: str,
    title: str,
    body: str,
    actor_user_id: int | None = None,
    payload: dict | None = None,
) -> None:
    db.add(
        SessionActivityEvent(
            game_session_id=game_session_id,
            actor_user_id=actor_user_id,
            event_type=event_type,
            title=title,
            body=body,
            payload=payload or {},
        )
    )


def _finalize_expired_auctions(db: Session, session_id: int) -> None:
    now = datetime.now(timezone.utc)
    expired_lots = db.execute(
        select(AuctionLot)
        .where(
            AuctionLot.game_session_id == session_id,
            AuctionLot.status == AuctionLotStatus.OPEN,
            AuctionLot.ends_at <= now,
        )
        .with_for_update()
    ).scalars().all()
    if not expired_lots:
        return

    for lot in expired_lots:
        item = db.execute(select(InventoryItem).where(InventoryItem.id == lot.inventory_item_id).with_for_update()).scalar_one_or_none()
        seller = db.get(User, lot.seller_user_id)
        bids = db.execute(
            select(AuctionBid)
            .where(AuctionBid.auction_lot_id == lot.id)
            .order_by(AuctionBid.bid_points.desc(), AuctionBid.created_at.asc(), AuctionBid.id.asc())
        ).scalars().all()

        winner_bid: AuctionBid | None = None
        for bid in bids:
            if get_player_balance(db, bid.bidder_user_id) >= bid.bid_points:
                winner_bid = bid
                break

        if not item or item.user_id != lot.seller_user_id or not winner_bid:
            lot.status = AuctionLotStatus.CLOSED_NO_WINNER
            lot.closed_at = now
            if seller:
                _log_session_event(
                    db,
                    game_session_id=session_id,
                    event_type="auction_closed_no_winner",
                    title="Лот закрыт без победителя",
                    body=f"Лот #{lot.id} завершен без успешной продажи",
                    actor_user_id=seller.id,
                    payload={"lot_id": lot.id},
                )
            continue

        winner = db.get(User, winner_bid.bidder_user_id)
        if not winner or not seller:
            lot.status = AuctionLotStatus.CLOSED_NO_WINNER
            lot.closed_at = now
            continue

        add_balance_event(
            db=db,
            user_id=winner.id,
            source=BalanceSource.MARKET_TRADE,
            amount=-winner_bid.bid_points,
            reason=f"Auction purchase lot #{lot.id}",
            game_session_id=session_id,
        )
        add_balance_event(
            db=db,
            user_id=seller.id,
            source=BalanceSource.MARKET_TRADE,
            amount=winner_bid.bid_points,
            reason=f"Auction sale lot #{lot.id}",
            game_session_id=session_id,
        )
        item.user_id = winner.id

        lot.status = AuctionLotStatus.CLOSED
        lot.closed_at = now
        lot.winner_user_id = winner.id
        lot.winning_bid_points = winner_bid.bid_points
        _log_session_event(
            db,
            game_session_id=session_id,
            event_type="auction_closed",
            title="Лот закрыт",
            body=f"{_user_identifier(winner)} выиграл лот #{lot.id} за {winner_bid.bid_points}",
            actor_user_id=winner.id,
            payload={"lot_id": lot.id, "winner_user_id": winner.id, "bid_points": winner_bid.bid_points},
        )


@router.get("/state")
def game_state(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    session = _get_active_session(db)
    if user.role == UserRole.PLAYER:
        _ensure_player_assigned(db, session.id, user.id)
    state = _get_or_create_player_state(db, user.id, session.id)
    normalized_position = _normalize_position(state.position, session.board_size)
    if normalized_position != state.position:
        state.position = normalized_position

    cells = db.execute(select(Cell).where(Cell.game_session_id == session.id).order_by(Cell.cell_index.asc())).scalars().all()
    inventory = db.execute(
        select(InventoryItem)
        .where(InventoryItem.user_id == user.id, InventoryItem.game_session_id == session.id)
        .order_by(InventoryItem.id.desc())
        .limit(50)
    ).scalars().all()
    shop_items = db.execute(select(SecretShopItem).where(SecretShopItem.is_active == 1).order_by(SecretShopItem.id.asc())).scalars().all()

    month_key = datetime.now(timezone.utc).strftime("%Y-%m")
    monthly_shop_count = db.execute(
        select(func.count())
        .select_from(SecretShopPurchase)
        .where(SecretShopPurchase.user_id == user.id, SecretShopPurchase.purchase_month == month_key)
    ).scalar_one()

    db.commit()

    return {
        "session": {
            "id": session.id,
            "name": session.name,
            "board_size": session.board_size,
            "max_rolls_per_window": session.max_rolls_per_window,
            "starts_at": session.starts_at.isoformat() if session.starts_at else None,
            "ends_at": session.ends_at.isoformat() if session.ends_at else None,
            "ended_at": session.ended_at.isoformat() if session.ended_at else None,
            "roll_window_config": session.roll_window_config,
        },
        "player": {
            "id": user.id,
            "email": user.email or user.phone or f"user-{user.id}",
            "token_asset": user.token_asset,
            "position": state.position,
            "balance": get_player_balance(db, user.id),
            "rolls_in_current_window": state.rolls_in_window,
            "monthly_secret_shop_purchases": int(monthly_shop_count),
            "secret_shop_monthly_limit": 3,
        },
        "cells": [
            {
                "id": c.id,
                "cell_index": c.cell_index,
                "title": c.title,
                "description": c.description,
                "reward_name": c.reward_name,
                "image_url": c.image_url,
                "price_points": c.price_points,
                "stock": c.stock,
                "status": c.status.value,
            }
            for c in cells
        ],
        "inventory": [
            {
                "id": i.id,
                "reward_name": i.reward_name,
                "paid_points": i.paid_points,
                "created_at": i.created_at.isoformat() if i.created_at else "",
            }
            for i in inventory
        ],
        "secret_shop": [
            {"id": s.id, "name": s.name, "price_points": s.price_points, "stock": s.stock}
            for s in shop_items
        ],
    }


@router.post("/roll", response_model=RollResponse)
def roll_dice(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> RollResponse:
    if user.role != UserRole.PLAYER:
        raise HTTPException(status_code=403, detail="Only players can roll")

    session = _get_active_session(db)
    _ensure_session_is_open(session)
    _ensure_player_assigned(db, session.id, user.id)
    state = _get_or_create_player_state(db, user.id, session.id)

    now = datetime.now(ZoneInfo(settings.app_timezone))
    slot_key = get_current_roll_slot_key(session.roll_window_config or [], now)
    if not slot_key:
        raise HTTPException(status_code=400, detail="Roll window is closed")

    if state.last_roll_slot_key != slot_key:
        state.rolls_in_window = 0

    if state.rolls_in_window >= session.max_rolls_per_window:
        raise HTTPException(
            status_code=400,
            detail=f"Roll limit reached for current window ({session.max_rolls_per_window})",
        )

    if session.board_size <= 0:
        raise HTTPException(status_code=400, detail="Board size is invalid")
    cells_by_index = {
        c.cell_index: c
        for c in db.execute(select(Cell).where(Cell.game_session_id == session.id)).scalars().all()
    }

    rolled = roll_d6()
    from_position = _normalize_position(state.position, session.board_size)
    to_position = (from_position + rolled) % session.board_size
    landed = cells_by_index.get(to_position)

    state.position = to_position
    state.rolls_in_window += 1
    state.last_roll_slot_key = slot_key
    state.last_roll_at = now

    db.add(
        MoveEvent(
            user_id=user.id,
            game_session_id=session.id,
            dice_value=rolled,
            from_position=from_position,
            to_position=to_position,
            cell_id=landed.id if landed else None,
        )
    )
    db.commit()

    return RollResponse(
        rolled=rolled,
        from_position=from_position,
        to_position=to_position,
        landed_cell={
            "id": landed.id,
            "title": landed.title,
            "reward_name": landed.reward_name,
            "price_points": landed.price_points,
            "stock": landed.stock,
            "status": landed.status.value,
            "action": "buy_or_skip",
        }
        if landed
        else None,
    )


@router.post("/cell/{cell_id}/purchase")
def purchase_cell_reward(
    cell_id: int,
    payload: CellPurchaseRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    if user.role != UserRole.PLAYER:
        raise HTTPException(status_code=403, detail="Only players can purchase")

    action = payload.action.lower().strip()
    if action not in {"buy", "skip"}:
        raise HTTPException(status_code=400, detail="Action must be 'buy' or 'skip'")
    if action == "skip":
        return {"status": "ok", "action": "skip"}

    session = _get_active_session(db)
    _ensure_session_is_open(session)
    _ensure_player_assigned(db, session.id, user.id)
    state = _get_or_create_player_state(db, user.id, session.id)

    landed = db.execute(
        select(Cell).where(Cell.game_session_id == session.id, Cell.cell_index == _normalize_position(state.position, session.board_size))
    ).scalar_one_or_none()
    if not landed:
        raise HTTPException(status_code=400, detail="No reward on current cell")
    if landed.id != cell_id:
        raise HTTPException(status_code=400, detail="Player is not on requested cell")

    locked_cell = db.execute(select(Cell).where(Cell.id == cell_id).with_for_update()).scalar_one_or_none()
    if not locked_cell:
        raise HTTPException(status_code=404, detail="Cell not found")
    if locked_cell.stock <= 0 or locked_cell.status == CellStatus.DEPLETED:
        locked_cell.stock = 0
        locked_cell.status = CellStatus.DEPLETED
        db.commit()
        raise HTTPException(status_code=400, detail="Cell is depleted")

    balance = get_player_balance(db, user.id)
    if balance < locked_cell.price_points:
        raise HTTPException(status_code=400, detail="Insufficient points")

    add_balance_event(
        db=db,
        user_id=user.id,
        source=BalanceSource.CELL_PURCHASE,
        amount=-locked_cell.price_points,
        reason=f"Purchased from cell #{locked_cell.cell_index}: {locked_cell.reward_name}",
        game_session_id=session.id,
    )
    db.add(
        InventoryItem(
            user_id=user.id,
            game_session_id=session.id,
            source_cell_id=locked_cell.id,
            reward_name=locked_cell.reward_name,
            paid_points=locked_cell.price_points,
        )
    )

    locked_cell.stock -= 1
    if locked_cell.stock <= 0:
        locked_cell.stock = 0
        locked_cell.status = CellStatus.DEPLETED

    db.commit()
    return {"status": "ok", "action": "buy", "balance": get_player_balance(db, user.id), "cell_stock": locked_cell.stock}


@router.post("/secret-shop/purchase")
def purchase_secret_shop(
    payload: SecretShopPurchaseRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    if user.role != UserRole.PLAYER:
        raise HTTPException(status_code=403, detail="Only players can purchase")
    session = _get_active_session(db)
    _ensure_session_is_open(session)
    _ensure_player_assigned(db, session.id, user.id)

    month_key = datetime.now(timezone.utc).strftime("%Y-%m")
    month_count = db.execute(
        select(func.count())
        .select_from(SecretShopPurchase)
        .where(SecretShopPurchase.user_id == user.id, SecretShopPurchase.purchase_month == month_key)
    ).scalar_one()
    if int(month_count) >= 3:
        raise HTTPException(status_code=400, detail="Secret shop monthly limit reached")

    item = db.execute(select(SecretShopItem).where(SecretShopItem.id == payload.item_id).with_for_update()).scalar_one_or_none()
    if not item or item.is_active != 1:
        raise HTTPException(status_code=404, detail="Secret shop item not found")
    if item.stock <= 0:
        raise HTTPException(status_code=400, detail="Secret shop item out of stock")

    balance = get_player_balance(db, user.id)
    if balance < item.price_points:
        raise HTTPException(status_code=400, detail="Insufficient points")

    add_balance_event(
        db=db,
        user_id=user.id,
        source=BalanceSource.SECRET_SHOP_PURCHASE,
        amount=-item.price_points,
        reason=f"Secret shop purchase: {item.name}",
        game_session_id=None,
    )
    db.add(SecretShopPurchase(user_id=user.id, secret_shop_item_id=item.id, purchase_month=month_key))
    db.add(
        InventoryItem(
            user_id=user.id,
            game_session_id=session.id,
            source_cell_id=None,
            reward_name=f"Secret shop: {item.name}",
            paid_points=item.price_points,
        )
    )
    item.stock -= 1

    db.commit()
    return {"status": "ok", "balance": get_player_balance(db, user.id), "monthly_purchases": int(month_count) + 1}


@router.get("/players")
def list_session_players(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    session = _get_active_session(db)
    _ensure_player_assigned(db, session.id, user.id)
    _finalize_expired_auctions(db, session.id)
    db.commit()
    players = _get_session_players(db, session.id)
    return {
        "items": [
            {
                "id": p.id,
                "identifier": p.email or p.phone or f"user-{p.id}",
                "balance": get_player_balance(db, p.id),
            }
            for p in players
        ]
    }


@router.get("/players/{player_id}/inventory")
def get_player_inventory(
    player_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    session = _get_active_session(db)
    _ensure_player_assigned(db, session.id, user.id)
    _finalize_expired_auctions(db, session.id)
    db.commit()
    _ensure_player_assigned(db, session.id, player_id)
    target = db.get(User, player_id)
    if not target or target.role != UserRole.PLAYER:
        raise HTTPException(status_code=404, detail="Player not found")

    items = db.execute(
        select(InventoryItem)
        .where(InventoryItem.user_id == player_id, InventoryItem.game_session_id == session.id)
        .order_by(InventoryItem.id.desc())
    ).scalars().all()
    return {
        "items": [
            {
                "id": i.id,
                "reward_name": i.reward_name,
                "paid_points": i.paid_points,
                "created_at": i.created_at.isoformat() if i.created_at else "",
            }
            for i in items
        ]
    }


@router.post("/market/offers")
def create_trade_offer(
    payload: TradeOfferCreateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    if user.role != UserRole.PLAYER:
        raise HTTPException(status_code=403, detail="Only players can trade")
    session = _get_active_session(db)
    _ensure_player_assigned(db, session.id, user.id)
    _ensure_player_assigned(db, session.id, payload.to_user_id)
    if payload.to_user_id == user.id:
        raise HTTPException(status_code=400, detail="Cannot create offer to yourself")
    _finalize_expired_auctions(db, session.id)

    item = db.execute(
        select(InventoryItem).where(
            InventoryItem.id == payload.inventory_item_id,
            InventoryItem.game_session_id == session.id,
        )
    ).scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    if item.user_id != payload.to_user_id:
        raise HTTPException(status_code=400, detail="Item does not belong to target player")
    open_lot_exists = db.execute(
        select(exists().where(AuctionLot.inventory_item_id == item.id, AuctionLot.status == AuctionLotStatus.OPEN))
    ).scalar_one()
    if open_lot_exists:
        raise HTTPException(status_code=400, detail="Item is currently listed in auction")

    existing_pending = db.execute(
        select(PlayerTradeOffer).where(
            PlayerTradeOffer.offered_item_id == item.id,
            PlayerTradeOffer.status == TradeOfferStatus.PENDING,
        )
    ).scalars().first()
    if existing_pending:
        raise HTTPException(status_code=400, detail="There is already a pending offer for this item")

    offer = PlayerTradeOffer(
        game_session_id=session.id,
        offered_item_id=item.id,
        from_user_id=user.id,
        to_user_id=payload.to_user_id,
        offer_points=payload.offer_points,
        status=TradeOfferStatus.PENDING,
        note=payload.note.strip(),
    )
    db.add(offer)
    _log_session_event(
        db=db,
        game_session_id=session.id,
        event_type="trade_offer_created",
        title="Новый оффер",
        body=f"{_user_identifier(user)} предложил {payload.offer_points} за '{item.reward_name}'",
        actor_user_id=user.id,
        payload={"offer_points": payload.offer_points, "to_user_id": payload.to_user_id, "item_id": item.id},
    )
    db.commit()
    db.refresh(offer)
    return {"status": "ok", "offer_id": offer.id}


@router.get("/market/offers")
def list_trade_offers(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    session = _get_active_session(db)
    _ensure_player_assigned(db, session.id, user.id)
    _finalize_expired_auctions(db, session.id)
    db.commit()
    offers = db.execute(
        select(PlayerTradeOffer)
        .where(
            PlayerTradeOffer.game_session_id == session.id,
            (PlayerTradeOffer.from_user_id == user.id) | (PlayerTradeOffer.to_user_id == user.id),
        )
        .order_by(PlayerTradeOffer.id.desc())
        .limit(200)
    ).scalars().all()

    user_ids = {o.from_user_id for o in offers} | {o.to_user_id for o in offers}
    users = db.execute(select(User).where(User.id.in_(list(user_ids)))).scalars().all() if user_ids else []
    user_map = {u.id: (u.email or u.phone or f"user-{u.id}") for u in users}

    item_ids = [o.offered_item_id for o in offers]
    items = db.execute(select(InventoryItem).where(InventoryItem.id.in_(item_ids))).scalars().all() if item_ids else []
    item_map = {i.id: i for i in items}

    return {
        "incoming": [
            {
                "id": o.id,
                "from_user_id": o.from_user_id,
                "from_identifier": user_map.get(o.from_user_id, f"user-{o.from_user_id}"),
                "to_user_id": o.to_user_id,
                "to_identifier": user_map.get(o.to_user_id, f"user-{o.to_user_id}"),
                "offer_points": o.offer_points,
                "status": o.status.value,
                "note": o.note,
                "created_at": o.created_at.isoformat() if o.created_at else "",
                "responded_at": o.responded_at.isoformat() if o.responded_at else None,
                "item": {
                    "id": item_map[o.offered_item_id].id,
                    "reward_name": item_map[o.offered_item_id].reward_name,
                }
                if o.offered_item_id in item_map
                else None,
            }
            for o in offers
            if o.to_user_id == user.id
        ],
        "outgoing": [
            {
                "id": o.id,
                "from_user_id": o.from_user_id,
                "from_identifier": user_map.get(o.from_user_id, f"user-{o.from_user_id}"),
                "to_user_id": o.to_user_id,
                "to_identifier": user_map.get(o.to_user_id, f"user-{o.to_user_id}"),
                "offer_points": o.offer_points,
                "status": o.status.value,
                "note": o.note,
                "created_at": o.created_at.isoformat() if o.created_at else "",
                "responded_at": o.responded_at.isoformat() if o.responded_at else None,
                "item": {
                    "id": item_map[o.offered_item_id].id,
                    "reward_name": item_map[o.offered_item_id].reward_name,
                }
                if o.offered_item_id in item_map
                else None,
            }
            for o in offers
            if o.from_user_id == user.id
        ],
    }


@router.post("/market/offers/{offer_id}/respond")
def respond_trade_offer(
    offer_id: int,
    payload: TradeOfferRespondRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    if user.role != UserRole.PLAYER:
        raise HTTPException(status_code=403, detail="Only players can respond to offers")
    session = _get_active_session(db)
    _ensure_player_assigned(db, session.id, user.id)
    _finalize_expired_auctions(db, session.id)

    offer = db.execute(
        select(PlayerTradeOffer)
        .where(PlayerTradeOffer.id == offer_id, PlayerTradeOffer.game_session_id == session.id)
        .with_for_update()
    ).scalar_one_or_none()
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")
    if offer.to_user_id != user.id:
        raise HTTPException(status_code=403, detail="Only recipient can respond")
    if offer.status != TradeOfferStatus.PENDING:
        raise HTTPException(status_code=400, detail="Offer is not pending")

    if payload.action == "reject":
        offer.status = TradeOfferStatus.REJECTED
        offer.responded_at = datetime.now(timezone.utc)
        _log_session_event(
            db=db,
            game_session_id=session.id,
            event_type="trade_offer_rejected",
            title="Оффер отклонен",
            body=f"{_user_identifier(user)} отклонил оффер #{offer.id}",
            actor_user_id=user.id,
            payload={"offer_id": offer.id},
        )
        db.commit()
        return {"status": "ok", "offer_status": offer.status.value}

    # accept flow
    item = db.execute(
        select(InventoryItem).where(
            InventoryItem.id == offer.offered_item_id,
            InventoryItem.game_session_id == session.id,
        ).with_for_update()
    ).scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=400, detail="Item no longer exists")
    if item.user_id != offer.to_user_id:
        raise HTTPException(status_code=400, detail="Item ownership changed")
    lot_open = db.execute(
        select(exists().where(AuctionLot.inventory_item_id == item.id, AuctionLot.status == AuctionLotStatus.OPEN))
    ).scalar_one()
    if lot_open:
        raise HTTPException(status_code=400, detail="Item is currently listed in auction")

    buyer_balance = get_player_balance(db, offer.from_user_id)
    if buyer_balance < offer.offer_points:
        raise HTTPException(status_code=400, detail="Buyer has insufficient points")

    add_balance_event(
        db=db,
        user_id=offer.from_user_id,
        source=BalanceSource.MARKET_TRADE,
        amount=-offer.offer_points,
        reason=f"Trade purchase offer #{offer.id}",
        game_session_id=session.id,
    )
    add_balance_event(
        db=db,
        user_id=offer.to_user_id,
        source=BalanceSource.MARKET_TRADE,
        amount=offer.offer_points,
        reason=f"Trade sale offer #{offer.id}",
        game_session_id=session.id,
    )

    item.user_id = offer.from_user_id
    offer.status = TradeOfferStatus.ACCEPTED
    offer.responded_at = datetime.now(timezone.utc)

    other_pending = db.execute(
        select(PlayerTradeOffer)
        .where(
            PlayerTradeOffer.offered_item_id == offer.offered_item_id,
            PlayerTradeOffer.id != offer.id,
            PlayerTradeOffer.status == TradeOfferStatus.PENDING,
        )
        .with_for_update()
    ).scalars().all()
    for other in other_pending:
        other.status = TradeOfferStatus.CANCELED
        other.responded_at = datetime.now(timezone.utc)

    buyer = db.get(User, offer.from_user_id)
    seller = db.get(User, offer.to_user_id)
    if buyer and seller:
        _log_session_event(
            db=db,
            game_session_id=session.id,
            event_type="trade_offer_accepted",
            title="Сделка завершена",
            body=f"{_user_identifier(buyer)} купил '{item.reward_name}' у {_user_identifier(seller)} за {offer.offer_points}",
            actor_user_id=user.id,
            payload={"offer_id": offer.id, "item_id": item.id, "amount": offer.offer_points},
        )

    db.commit()
    return {"status": "ok", "offer_status": offer.status.value}


@router.post("/market/auctions")
def create_auction_lot(
    payload: AuctionLotCreateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    if user.role != UserRole.PLAYER:
        raise HTTPException(status_code=403, detail="Only players can create auctions")
    session = _get_active_session(db)
    _ensure_session_is_open(session)
    _ensure_player_assigned(db, session.id, user.id)
    _finalize_expired_auctions(db, session.id)

    item = db.execute(
        select(InventoryItem)
        .where(
            InventoryItem.id == payload.inventory_item_id,
            InventoryItem.game_session_id == session.id,
            InventoryItem.user_id == user.id,
        )
        .with_for_update()
    ).scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")

    pending_offer_exists = db.execute(
        select(exists().where(PlayerTradeOffer.offered_item_id == item.id, PlayerTradeOffer.status == TradeOfferStatus.PENDING))
    ).scalar_one()
    if pending_offer_exists:
        raise HTTPException(status_code=400, detail="There is a pending direct offer for this item")

    open_lot_exists = db.execute(
        select(exists().where(AuctionLot.inventory_item_id == item.id, AuctionLot.status == AuctionLotStatus.OPEN))
    ).scalar_one()
    if open_lot_exists:
        raise HTTPException(status_code=400, detail="Item is already listed in auction")

    now = datetime.now(timezone.utc)
    lot = AuctionLot(
        game_session_id=session.id,
        inventory_item_id=item.id,
        seller_user_id=user.id,
        starts_at=now,
        ends_at=now + timedelta(minutes=payload.duration_minutes),
        status=AuctionLotStatus.OPEN,
    )
    db.add(lot)
    db.flush()
    _log_session_event(
        db=db,
        game_session_id=session.id,
        event_type="auction_opened",
        title="Открыт аукцион",
        body=f"{_user_identifier(user)} выставил '{item.reward_name}' до {lot.ends_at.isoformat()}",
        actor_user_id=user.id,
        payload={"lot_id": lot.id, "item_id": item.id, "ends_at": lot.ends_at.isoformat()},
    )
    db.commit()
    return {"status": "ok", "lot_id": lot.id}


@router.post("/market/auctions/{lot_id}/bid")
def place_auction_bid(
    lot_id: int,
    payload: AuctionBidRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    if user.role != UserRole.PLAYER:
        raise HTTPException(status_code=403, detail="Only players can bid")
    session = _get_active_session(db)
    _ensure_session_is_open(session)
    _ensure_player_assigned(db, session.id, user.id)
    _finalize_expired_auctions(db, session.id)

    lot = db.execute(
        select(AuctionLot)
        .where(AuctionLot.id == lot_id, AuctionLot.game_session_id == session.id)
        .with_for_update()
    ).scalar_one_or_none()
    if not lot:
        raise HTTPException(status_code=404, detail="Auction lot not found")
    if lot.status != AuctionLotStatus.OPEN:
        raise HTTPException(status_code=400, detail="Auction lot is closed")
    if lot.seller_user_id == user.id:
        raise HTTPException(status_code=400, detail="Seller cannot bid on own lot")
    if lot.ends_at <= datetime.now(timezone.utc):
        _finalize_expired_auctions(db, session.id)
        db.commit()
        raise HTTPException(status_code=400, detail="Auction lot is closed")

    current_max = db.execute(
        select(func.max(AuctionBid.bid_points)).where(AuctionBid.auction_lot_id == lot.id)
    ).scalar_one()
    min_required = int(current_max or 0) + 1
    if payload.bid_points < min_required:
        raise HTTPException(status_code=400, detail=f"Bid must be >= {min_required}")
    if get_player_balance(db, user.id) < payload.bid_points:
        raise HTTPException(status_code=400, detail="Insufficient points for bid")

    bid = AuctionBid(auction_lot_id=lot.id, bidder_user_id=user.id, bid_points=payload.bid_points)
    db.add(bid)

    item = db.get(InventoryItem, lot.inventory_item_id)
    _log_session_event(
        db=db,
        game_session_id=session.id,
        event_type="auction_bid_placed",
        title="Новая ставка",
        body=f"{_user_identifier(user)} поставил {payload.bid_points} на '{item.reward_name if item else f'лот #{lot.id}'}'",
        actor_user_id=user.id,
        payload={"lot_id": lot.id, "bid_points": payload.bid_points},
    )
    db.commit()
    return {"status": "ok"}


@router.get("/market/auctions")
def list_auction_lots(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    session = _get_active_session(db)
    _ensure_player_assigned(db, session.id, user.id)
    _finalize_expired_auctions(db, session.id)
    db.commit()

    lots = db.execute(
        select(AuctionLot)
        .where(AuctionLot.game_session_id == session.id)
        .order_by(AuctionLot.id.desc())
        .limit(200)
    ).scalars().all()
    lot_ids = [l.id for l in lots]
    item_ids = [l.inventory_item_id for l in lots]
    user_ids = {l.seller_user_id for l in lots} | {l.winner_user_id for l in lots if l.winner_user_id}

    bids = db.execute(
        select(AuctionBid).where(AuctionBid.auction_lot_id.in_(lot_ids)).order_by(AuctionBid.bid_points.desc(), AuctionBid.id.asc())
    ).scalars().all() if lot_ids else []
    top_bid_by_lot: dict[int, AuctionBid] = {}
    for bid in bids:
        if bid.auction_lot_id not in top_bid_by_lot:
            top_bid_by_lot[bid.auction_lot_id] = bid
            user_ids.add(bid.bidder_user_id)

    users = db.execute(select(User).where(User.id.in_(list(user_ids)))).scalars().all() if user_ids else []
    user_map = {u.id: _user_identifier(u) for u in users}
    items = db.execute(select(InventoryItem).where(InventoryItem.id.in_(item_ids))).scalars().all() if item_ids else []
    item_map = {i.id: i for i in items}

    return {
        "items": [
            {
                "id": lot.id,
                "inventory_item_id": lot.inventory_item_id,
                "item_name": item_map[lot.inventory_item_id].reward_name if lot.inventory_item_id in item_map else f"Item #{lot.inventory_item_id}",
                "seller_user_id": lot.seller_user_id,
                "seller_identifier": user_map.get(lot.seller_user_id, f"user-{lot.seller_user_id}"),
                "status": lot.status.value,
                "starts_at": lot.starts_at.isoformat() if lot.starts_at else None,
                "ends_at": lot.ends_at.isoformat() if lot.ends_at else None,
                "closed_at": lot.closed_at.isoformat() if lot.closed_at else None,
                "winner_user_id": lot.winner_user_id,
                "winner_identifier": user_map.get(lot.winner_user_id) if lot.winner_user_id else None,
                "winning_bid_points": lot.winning_bid_points,
                "top_bid_points": top_bid_by_lot[lot.id].bid_points if lot.id in top_bid_by_lot else None,
                "top_bidder_user_id": top_bid_by_lot[lot.id].bidder_user_id if lot.id in top_bid_by_lot else None,
                "top_bidder_identifier": user_map.get(top_bid_by_lot[lot.id].bidder_user_id) if lot.id in top_bid_by_lot else None,
            }
            for lot in lots
        ]
    }


@router.get("/market/activity")
def market_activity_feed(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    session = _get_active_session(db)
    _ensure_player_assigned(db, session.id, user.id)
    _finalize_expired_auctions(db, session.id)
    db.commit()

    events = db.execute(
        select(SessionActivityEvent)
        .where(SessionActivityEvent.game_session_id == session.id)
        .order_by(SessionActivityEvent.id.desc())
        .limit(200)
    ).scalars().all()

    return {
        "items": [
            {
                "id": e.id,
                "event_type": e.event_type,
                "title": e.title,
                "body": e.body,
                "payload": e.payload,
                "created_at": e.created_at.isoformat() if e.created_at else "",
            }
            for e in events
        ]
    }


@router.get("/market/rating")
def market_rating(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    session = _get_active_session(db)
    _ensure_player_assigned(db, session.id, user.id)
    _finalize_expired_auctions(db, session.id)
    db.commit()

    players = _get_session_players(db, session.id)
    if not players:
        return {"items": []}

    player_ids = [p.id for p in players]
    inv_rows = db.execute(
        select(InventoryItem.user_id, func.coalesce(func.sum(InventoryItem.paid_points), 0))
        .where(InventoryItem.game_session_id == session.id, InventoryItem.user_id.in_(player_ids))
        .group_by(InventoryItem.user_id)
    ).all()
    inv_sum = {int(uid): int(total) for uid, total in inv_rows}

    items = []
    for p in players:
        balance = get_player_balance(db, p.id)
        inventory_value = inv_sum.get(p.id, 0)
        total = balance + inventory_value
        items.append(
            {
                "user_id": p.id,
                "identifier": _user_identifier(p),
                "balance": balance,
                "inventory_value": inventory_value,
                "total_score": total,
            }
        )

    items.sort(key=lambda x: (-x["total_score"], x["user_id"]))
    for idx, row in enumerate(items, start=1):
        row["rank"] = idx

    return {"items": items}
