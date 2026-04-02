from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Literal
from uuid import uuid4

CellType = Literal["neutral", "reward_points", "penalty_points"]
Role = Literal["admin", "player"]


@dataclass
class Cell:
    index: int
    kind: CellType
    value: int
    title: str


@dataclass
class Reward:
    id: str
    name: str
    cost: int
    stock: int


@dataclass
class Move:
    rolled: int
    from_position: int
    to_position: int
    cell_kind: CellType
    effect_value: int
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass
class User:
    id: str
    email: str
    password: str
    role: Role
    position: int = 0
    balance: int = 0
    moves: list[Move] = field(default_factory=list)
    owned_rewards: list[str] = field(default_factory=list)


users: dict[str, User] = {}
sessions: dict[str, str] = {}

board: list[Cell] = [
    Cell(index=0, kind="neutral", value=0, title="Старт"),
    Cell(index=1, kind="reward_points", value=10, title="Мини-продажа"),
    Cell(index=2, kind="penalty_points", value=5, title="Штраф за просрочку"),
    Cell(index=3, kind="reward_points", value=20, title="Крупная сделка"),
    Cell(index=4, kind="neutral", value=0, title="Передышка"),
    Cell(index=5, kind="penalty_points", value=15, title="Потеря клиента"),
    Cell(index=6, kind="reward_points", value=30, title="Супер-продажа"),
    Cell(index=7, kind="neutral", value=0, title="Лаки-зона"),
]

rewards: dict[str, Reward] = {
    "gift-10": Reward(id="gift-10", name="Кофе-сертификат", cost=40, stock=100),
    "gift-20": Reward(id="gift-20", name="Мерч-набор", cost=120, stock=50),
    "gift-30": Reward(id="gift-30", name="Главный приз", cost=300, stock=10),
}

users["admin@demo.local"] = User(id=str(uuid4()), email="admin@demo.local", password="admin", role="admin")
users["player@demo.local"] = User(id=str(uuid4()), email="player@demo.local", password="player", role="player")
