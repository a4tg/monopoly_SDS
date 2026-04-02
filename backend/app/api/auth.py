from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.config import settings
from app.core.security import (
    create_token_pair,
    decode_token,
    hash_password,
    is_phone,
    needs_rehash,
    normalize_email,
    normalize_phone,
    verify_password,
)
from app.core.tokens import pick_random_token_asset
from app.db.session import get_db
from app.models import PasswordResetToken, PlayerNotification, User, UserRole
from app.schemas.auth import (
    LoginRequest,
    MeResponse,
    NotificationResponse,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)

router = APIRouter()
logger = logging.getLogger(__name__)


def _find_user_by_identifier(db: Session, identifier: str) -> User | None:
    normalized = identifier.strip()
    if "@" in normalized:
        return db.execute(select(User).where(User.email == normalize_email(normalized))).scalar_one_or_none()

    phone = normalize_phone(normalized)
    if not is_phone(phone):
        return None
    return db.execute(select(User).where(User.phone == phone)).scalar_one_or_none()


def _token_response_for_user(user: User) -> TokenResponse:
    access_token, refresh_token = create_token_pair(user.id, user.role.value)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


def _hash_reset_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@router.post("/register", response_model=TokenResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    email = normalize_email(payload.email) if payload.email else None
    phone = normalize_phone(payload.phone) if payload.phone else None

    if phone and not is_phone(phone):
        raise HTTPException(status_code=400, detail="Invalid phone format")

    if email:
        existing_email = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
        if existing_email:
            raise HTTPException(status_code=400, detail="User with this email already exists")
    if phone:
        existing_phone = db.execute(select(User).where(User.phone == phone)).scalar_one_or_none()
        if existing_phone:
            raise HTTPException(status_code=400, detail="User with this phone already exists")

    role = UserRole.ADMIN if payload.role == "admin" else UserRole.PLAYER
    user = User(
        email=email,
        phone=phone,
        password=hash_password(payload.password),
        role=role,
        token_asset=pick_random_token_asset(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _token_response_for_user(user)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = _find_user_by_identifier(db, payload.identifier)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    password_ok = False
    if user.password.startswith("$"):
        password_ok = verify_password(payload.password, user.password)
        if password_ok and needs_rehash(user.password):
            user.password = hash_password(payload.password)
            db.commit()
    else:
        # Backward-compatible path for pre-alpha plaintext users.
        password_ok = user.password == payload.password
        if password_ok:
            user.password = hash_password(payload.password)
            db.commit()

    if not password_ok:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return _token_response_for_user(user)


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> TokenResponse:
    try:
        token_payload = decode_token(payload.refresh_token, expected_type="refresh")
        user_id = int(token_payload.get("sub"))
    except (ValueError, TypeError):
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    return _token_response_for_user(user)


@router.get("/me", response_model=MeResponse)
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> MeResponse:
    del db
    identifier = user.email or user.phone or f"user-{user.id}"
    return MeResponse(
        id=user.id,
        email=user.email,
        phone=user.phone,
        identifier=identifier,
        token_asset=user.token_asset,
        role=user.role.value,
    )


@router.post("/password-reset/request")
def request_password_reset(payload: PasswordResetRequest, db: Session = Depends(get_db)) -> dict:
    email = normalize_email(payload.email)
    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    now = datetime.now(timezone.utc)

    if user:
        active_tokens = db.execute(
            select(PasswordResetToken).where(
                PasswordResetToken.user_id == user.id,
                PasswordResetToken.used_at.is_(None),
            )
        ).scalars().all()
        for row in active_tokens:
            row.used_at = now

        raw_token = secrets.token_urlsafe(32)
        db.add(
            PasswordResetToken(
                user_id=user.id,
                token_hash=_hash_reset_token(raw_token),
                expires_at=now + timedelta(minutes=settings.password_reset_ttl_minutes),
            )
        )
        db.commit()

        reset_link = f"{settings.password_reset_link_base_url}?token={raw_token}"
        logger.info("Password reset link for %s: %s", email, reset_link)

    return {
        "status": "ok",
        "message": "If the email exists, a reset link has been sent.",
    }


@router.post("/password-reset/confirm")
def confirm_password_reset(payload: PasswordResetConfirmRequest, db: Session = Depends(get_db)) -> dict:
    now = datetime.now(timezone.utc)
    token_hash = _hash_reset_token(payload.token)
    reset = db.execute(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.used_at.is_(None),
        )
    ).scalar_one_or_none()
    if not reset or reset.expires_at < now:
        raise HTTPException(status_code=400, detail="Reset token is invalid or expired")

    user = db.get(User, reset.user_id)
    if not user:
        raise HTTPException(status_code=400, detail="Reset token is invalid or expired")

    user.password = hash_password(payload.new_password)
    reset.used_at = now
    db.commit()
    return {"status": "ok"}


@router.get("/notifications/unread")
def unread_notifications(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    notifications = db.execute(
        select(PlayerNotification)
        .where(PlayerNotification.user_id == user.id, PlayerNotification.is_read == 0)
        .order_by(PlayerNotification.created_at.desc())
        .limit(20)
    ).scalars().all()

    items = [
        NotificationResponse(
            id=n.id,
            type=n.type.value,
            title=n.title,
            body=n.body,
            created_at=n.created_at.astimezone(timezone.utc).isoformat() if n.created_at else "",
        ).model_dump()
        for n in notifications
    ]

    return {"items": items}


@router.post("/notifications/read-all")
def read_all_notifications(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    rows = db.execute(
        select(PlayerNotification).where(PlayerNotification.user_id == user.id, PlayerNotification.is_read == 0)
    ).scalars().all()
    for row in rows:
        row.is_read = 1
    db.commit()
    return {"status": "ok", "updated": len(rows)}


@router.post("/logout")
def logout(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    del user
    del db
    return {"status": "ok"}
