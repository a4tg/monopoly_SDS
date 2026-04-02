from __future__ import annotations

import csv
import io
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.auth import require_admin
from app.db.session import get_db
from app.models import (
    BalanceSource,
    Cell,
    CellStatus,
    GameSession,
    InventoryItem,
    MoveEvent,
    NotificationType,
    PlayerBalanceEvent,
    PlayerNotification,
    PlayerSessionState,
    SecretShopItem,
    SessionParticipant,
    SessionStatus,
    User,
    UserRole,
)
from app.schemas.admin import (
    AccrualRequest,
    CellCreateRequest,
    CellUpdateRequest,
    SecretShopCreateRequest,
    SecretShopUpdateRequest,
    SessionCreateRequest,
    SessionScheduleUpdateRequest,
    SessionParticipantsAssignRequest,
    SessionStatusRequest,
)
from app.services.balance import add_balance_event, get_player_balance

router = APIRouter()


def _session_to_dict(s: GameSession) -> dict:
    return {
        "id": s.id,
        "name": s.name,
        "status": s.status.value,
        "board_size": s.board_size,
        "max_rolls_per_window": s.max_rolls_per_window,
        "starts_at": s.starts_at.isoformat() if s.starts_at else None,
        "ends_at": s.ends_at.isoformat() if s.ends_at else None,
        "ended_at": s.ended_at.isoformat() if s.ended_at else None,
        "roll_window_config": s.roll_window_config,
    }


@router.post("/sessions")
def create_session(
    payload: SessionCreateRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    del admin
    if payload.starts_at and payload.ends_at and payload.starts_at >= payload.ends_at:
        raise HTTPException(status_code=400, detail="starts_at must be earlier than ends_at")

    session = GameSession(
        name=payload.name,
        status=SessionStatus.DRAFT,
        board_size=payload.board_size,
        max_rolls_per_window=payload.max_rolls_per_window,
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
        roll_window_config=[s.model_dump() for s in payload.roll_window_config],
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return {"status": "ok", "session": _session_to_dict(session)}


@router.patch("/sessions/{session_id}/status")
def set_session_status(
    session_id: int,
    payload: SessionStatusRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    del admin
    session = db.get(GameSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    new_status = SessionStatus(payload.status)
    session.status = new_status
    if new_status == SessionStatus.CLOSED and session.ended_at is None:
        session.ended_at = datetime.now(timezone.utc)
    if new_status != SessionStatus.CLOSED:
        session.ended_at = None
    db.commit()
    return {"status": "ok", "session": _session_to_dict(session)}


@router.patch("/sessions/{session_id}/schedule")
def update_session_schedule(
    session_id: int,
    payload: SessionScheduleUpdateRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    del admin
    session = db.get(GameSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    starts_at = payload.starts_at if payload.starts_at is not None else session.starts_at
    ends_at = payload.ends_at if payload.ends_at is not None else session.ends_at
    if starts_at and ends_at and starts_at >= ends_at:
        raise HTTPException(status_code=400, detail="starts_at must be earlier than ends_at")

    if payload.starts_at is not None:
        session.starts_at = payload.starts_at
    if payload.ends_at is not None:
        session.ends_at = payload.ends_at
    if payload.max_rolls_per_window is not None:
        session.max_rolls_per_window = payload.max_rolls_per_window
    if payload.board_size is not None:
        session.board_size = payload.board_size
    if payload.roll_window_config is not None:
        session.roll_window_config = [slot.model_dump() for slot in payload.roll_window_config]

    db.commit()
    db.refresh(session)
    return {"status": "ok", "session": _session_to_dict(session)}


@router.post("/sessions/{session_id}/end")
def end_session_now(
    session_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    del admin
    session = db.get(GameSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session.status = SessionStatus.CLOSED
    session.ended_at = datetime.now(timezone.utc)
    db.commit()
    return {"status": "ok", "session": _session_to_dict(session)}


@router.get("/sessions")
def list_sessions(admin: User = Depends(require_admin), db: Session = Depends(get_db)) -> list[dict]:
    del admin
    sessions = db.execute(select(GameSession).order_by(GameSession.id.desc())).scalars().all()
    return [_session_to_dict(s) for s in sessions]


@router.post("/sessions/{session_id}/participants")
def set_session_participants(
    session_id: int,
    payload: SessionParticipantsAssignRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    session = db.get(GameSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if not payload.player_ids:
        db.execute(delete(SessionParticipant).where(SessionParticipant.game_session_id == session_id))
        db.commit()
        return {"status": "ok", "assigned": 0}

    players = db.execute(
        select(User).where(User.id.in_(payload.player_ids), User.role == UserRole.PLAYER)
    ).scalars().all()
    found_ids = {p.id for p in players}
    missing = sorted(set(payload.player_ids) - found_ids)
    if missing:
        raise HTTPException(status_code=400, detail=f"Unknown player ids: {missing}")

    db.execute(delete(SessionParticipant).where(SessionParticipant.game_session_id == session_id))
    for player in players:
        db.add(
            SessionParticipant(
                game_session_id=session_id,
                user_id=player.id,
                assigned_by_user_id=admin.id,
            )
        )
    db.commit()
    return {"status": "ok", "assigned": len(players)}


@router.get("/sessions/{session_id}/participants")
def get_session_participants(
    session_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    del admin
    session = db.get(GameSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    items = db.execute(
        select(SessionParticipant, User)
        .join(User, User.id == SessionParticipant.user_id)
        .where(SessionParticipant.game_session_id == session_id)
        .order_by(User.id.asc())
    ).all()

    return {
        "items": [
            {
                "user_id": u.id,
                "identifier": u.email or u.phone or f"user-{u.id}",
                "assigned_at": sp.assigned_at.isoformat() if sp.assigned_at else None,
            }
            for sp, u in items
        ]
    }


@router.get("/sessions/{session_id}/results")
def export_session_results(
    session_id: int,
    format: str = Query(default="json", pattern="^(json|csv)$"),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    del admin
    session = db.get(GameSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    participants = db.execute(
        select(User)
        .join(SessionParticipant, SessionParticipant.user_id == User.id)
        .where(SessionParticipant.game_session_id == session_id)
        .order_by(User.id.asc())
    ).scalars().all()

    rows: list[dict] = []
    for user in participants:
        moves_count = db.execute(
            select(func.count())
            .select_from(MoveEvent)
            .where(MoveEvent.game_session_id == session_id, MoveEvent.user_id == user.id)
        ).scalar_one()
        inventory_count = db.execute(
            select(func.count())
            .select_from(InventoryItem)
            .where(InventoryItem.game_session_id == session_id, InventoryItem.user_id == user.id)
        ).scalar_one()
        state = db.execute(
            select(PlayerSessionState).where(
                PlayerSessionState.game_session_id == session_id,
                PlayerSessionState.user_id == user.id,
            )
        ).scalar_one_or_none()

        rows.append(
            {
                "user_id": user.id,
                "identifier": user.email or user.phone or f"user-{user.id}",
                "balance": int(
                    db.execute(
                        select(func.coalesce(func.sum(PlayerBalanceEvent.amount), 0)).where(
                            PlayerBalanceEvent.game_session_id == session_id,
                            PlayerBalanceEvent.user_id == user.id,
                        )
                    ).scalar_one()
                ),
                "moves_count": int(moves_count),
                "inventory_count": int(inventory_count),
                "position": state.position if state else 0,
            }
        )

    rows.sort(key=lambda x: (-x["balance"], -x["moves_count"], x["user_id"]))

    if format == "json":
        return {"session": _session_to_dict(session), "results": rows}

    out = io.StringIO()
    writer = csv.DictWriter(
        out,
        fieldnames=["user_id", "identifier", "balance", "moves_count", "inventory_count", "position"],
    )
    writer.writeheader()
    writer.writerows(rows)
    csv_data = out.getvalue()
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="session_{session_id}_results.csv"'},
    )


@router.post("/sessions/{session_id}/cells")
def create_cell(
    session_id: int,
    payload: CellCreateRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    del admin
    session = db.get(GameSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    exists = db.execute(
        select(Cell).where(Cell.game_session_id == session_id, Cell.cell_index == payload.cell_index)
    ).scalar_one_or_none()
    if exists:
        raise HTTPException(status_code=400, detail="Cell index already exists")
    if payload.cell_index >= session.board_size:
        raise HTTPException(status_code=400, detail=f"Cell index must be less than board_size ({session.board_size})")

    status = CellStatus.ACTIVE if payload.stock > 0 else CellStatus.DEPLETED
    cell = Cell(
        game_session_id=session_id,
        cell_index=payload.cell_index,
        title=payload.title,
        description=payload.description,
        reward_name=payload.reward_name,
        image_url=payload.image_url,
        price_points=payload.price_points,
        stock=payload.stock,
        status=status,
    )
    db.add(cell)
    db.commit()
    db.refresh(cell)
    return {"status": "ok", "cell": {"id": cell.id, "index": cell.cell_index, "title": cell.title}}


@router.get("/sessions/{session_id}/cells")
def list_cells(session_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)) -> list[dict]:
    del admin
    cells = db.execute(
        select(Cell).where(Cell.game_session_id == session_id).order_by(Cell.cell_index.asc())
    ).scalars().all()
    return [
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
    ]


@router.patch("/cells/{cell_id}")
def update_cell(
    cell_id: int,
    payload: CellUpdateRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    del admin
    cell = db.get(Cell, cell_id)
    if not cell:
        raise HTTPException(status_code=404, detail="Cell not found")

    if payload.title is not None:
        cell.title = payload.title
    if payload.description is not None:
        cell.description = payload.description
    if payload.reward_name is not None:
        cell.reward_name = payload.reward_name
    if payload.image_url is not None:
        cell.image_url = payload.image_url
    if payload.price_points is not None:
        cell.price_points = payload.price_points
    if payload.stock is not None:
        cell.stock = payload.stock

    cell.status = CellStatus.ACTIVE if cell.stock > 0 else CellStatus.DEPLETED
    db.commit()
    return {"status": "ok"}


@router.post("/players/{player_id}/accrual")
def manual_accrual(
    player_id: int,
    payload: AccrualRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    target = db.get(User, player_id)
    if not target or target.role != UserRole.PLAYER:
        raise HTTPException(status_code=404, detail="Player not found")

    add_balance_event(
        db=db,
        user_id=target.id,
        source=BalanceSource.ADMIN_MANUAL,
        amount=payload.points,
        reason=f"Admin {admin.email}: {payload.reason}",
        game_session_id=None,
    )
    db.add(
        PlayerNotification(
            user_id=target.id,
            type=NotificationType.MANUAL_ACCRUAL,
            title="Points credited",
            body=f"+{payload.points} points. Reason: {payload.reason}",
        )
    )
    db.commit()
    return {"status": "ok", "player_id": target.id, "balance": get_player_balance(db, target.id)}


@router.get("/participants")
def participants(admin: User = Depends(require_admin), db: Session = Depends(get_db)) -> list[dict]:
    del admin
    players = db.execute(select(User).where(User.role == UserRole.PLAYER).order_by(User.id.asc())).scalars().all()
    result: list[dict] = []
    for p in players:
        balance = get_player_balance(db, p.id)
        moves = db.execute(select(func.count()).select_from(PlayerSessionState).where(PlayerSessionState.user_id == p.id)).scalar_one()
        result.append(
            {
                "id": p.id,
                "email": p.email or p.phone or f"user-{p.id}",
                "balance": balance,
                "sessions_joined": int(moves),
            }
        )
    return result


@router.get("/secret-shop/items")
def list_secret_shop(admin: User = Depends(require_admin), db: Session = Depends(get_db)) -> list[dict]:
    del admin
    items = db.execute(select(SecretShopItem).order_by(SecretShopItem.id.asc())).scalars().all()
    return [
        {"id": i.id, "name": i.name, "price_points": i.price_points, "stock": i.stock, "is_active": i.is_active}
        for i in items
    ]


@router.post("/secret-shop/items")
def create_secret_shop_item(
    payload: SecretShopCreateRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    del admin
    item = SecretShopItem(name=payload.name, price_points=payload.price_points, stock=payload.stock, is_active=1)
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"status": "ok", "item_id": item.id}


@router.patch("/secret-shop/items/{item_id}")
def update_secret_shop_item(
    item_id: int,
    payload: SecretShopUpdateRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    del admin
    item = db.get(SecretShopItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Secret shop item not found")

    if payload.name is not None:
        item.name = payload.name
    if payload.price_points is not None:
        item.price_points = payload.price_points
    if payload.stock is not None:
        item.stock = payload.stock
    if payload.is_active is not None:
        item.is_active = payload.is_active

    db.commit()
    return {"status": "ok"}
