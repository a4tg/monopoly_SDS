from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class LoginRequest(BaseModel):
    identifier: str = Field(min_length=3, max_length=320, description="Email or phone")
    password: str = Field(min_length=3, max_length=128)


class RegisterRequest(BaseModel):
    email: str | None = Field(default=None, min_length=3, max_length=320)
    phone: str | None = Field(default=None, min_length=10, max_length=32)
    password: str = Field(min_length=3, max_length=128)
    role: str = Field(default="player", pattern="^(player|admin)$")

    @model_validator(mode="after")
    def validate_identifier(self) -> "RegisterRequest":
        if not self.email and not self.phone:
            raise ValueError("At least one of email or phone is required")
        return self


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str


class MeResponse(BaseModel):
    id: int
    email: str | None
    phone: str | None
    identifier: str
    token_asset: str
    role: str


class RefreshRequest(BaseModel):
    refresh_token: str


class NotificationResponse(BaseModel):
    id: int
    type: str
    title: str
    body: str
    created_at: str


class PasswordResetRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)


class PasswordResetConfirmRequest(BaseModel):
    token: str = Field(min_length=16, max_length=512)
    new_password: str = Field(min_length=6, max_length=128)
