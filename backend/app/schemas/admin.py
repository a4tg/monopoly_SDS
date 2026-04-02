from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class RollWindowSlot(BaseModel):
    days: list[int] = Field(default_factory=list)
    start: str = Field(description="HH:MM")
    end: str = Field(description="HH:MM")


class SessionCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    board_size: int = Field(default=40, ge=4, le=40)
    max_rolls_per_window: int = Field(default=1, ge=1, le=20)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    roll_window_config: list[RollWindowSlot] = Field(default_factory=list)


class SessionParticipantsAssignRequest(BaseModel):
    player_ids: list[int] = Field(default_factory=list)


class SessionScheduleUpdateRequest(BaseModel):
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    board_size: int | None = Field(default=None, ge=4, le=40)
    max_rolls_per_window: int | None = Field(default=None, ge=1, le=20)
    roll_window_config: list[RollWindowSlot] | None = None


class SessionStatusRequest(BaseModel):
    status: str = Field(pattern="^(draft|active|closed)$")


class CellCreateRequest(BaseModel):
    cell_index: int = Field(ge=0, le=1000)
    title: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=500)
    reward_name: str = Field(min_length=1, max_length=120)
    image_url: str | None = Field(default=None, max_length=2000)
    price_points: int = Field(ge=0, le=1_000_000)
    stock: int = Field(ge=0, le=1_000_000)


class CellUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    reward_name: str | None = Field(default=None, min_length=1, max_length=120)
    image_url: str | None = Field(default=None, max_length=2000)
    price_points: int | None = Field(default=None, ge=0, le=1_000_000)
    stock: int | None = Field(default=None, ge=0, le=1_000_000)


class AccrualRequest(BaseModel):
    points: int = Field(ge=1, le=1_000_000)
    reason: str = Field(min_length=1, max_length=255)


class SecretShopCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    price_points: int = Field(ge=1, le=1_000_000)
    stock: int = Field(ge=0, le=1_000_000)


class SecretShopUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    price_points: int | None = Field(default=None, ge=1, le=1_000_000)
    stock: int | None = Field(default=None, ge=0, le=1_000_000)
    is_active: int | None = Field(default=None, ge=0, le=1)
