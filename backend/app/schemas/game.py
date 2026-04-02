from __future__ import annotations

from pydantic import BaseModel, Field


class RollResponse(BaseModel):
    rolled: int
    from_position: int
    to_position: int
    landed_cell: dict | None


class CellPurchaseRequest(BaseModel):
    action: str


class SecretShopPurchaseRequest(BaseModel):
    item_id: int


class TradeOfferCreateRequest(BaseModel):
    inventory_item_id: int
    to_user_id: int
    offer_points: int = Field(ge=1, le=1_000_000)
    note: str = Field(default="", max_length=255)


class TradeOfferRespondRequest(BaseModel):
    action: str = Field(pattern="^(accept|reject)$")


class AuctionLotCreateRequest(BaseModel):
    inventory_item_id: int
    duration_minutes: int = Field(ge=1, le=10080)


class AuctionBidRequest(BaseModel):
    bid_points: int = Field(ge=1, le=1_000_000_000)
