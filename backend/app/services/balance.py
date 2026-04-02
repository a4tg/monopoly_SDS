from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import BalanceSource, PlayerBalanceEvent


def get_player_balance(db: Session, user_id: int) -> int:
    stmt = select(func.coalesce(func.sum(PlayerBalanceEvent.amount), 0)).where(PlayerBalanceEvent.user_id == user_id)
    balance = db.execute(stmt).scalar_one()
    return int(balance)


def add_balance_event(
    db: Session,
    user_id: int,
    source: BalanceSource,
    amount: int,
    reason: str,
    game_session_id: int | None = None,
) -> PlayerBalanceEvent:
    event = PlayerBalanceEvent(
        user_id=user_id,
        source=source,
        amount=amount,
        reason=reason,
        game_session_id=game_session_id,
    )
    db.add(event)
    return event
