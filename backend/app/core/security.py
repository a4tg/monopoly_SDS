from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

PHONE_REGEX = re.compile(r"^\+?[1-9]\d{9,14}$")


def normalize_email(value: str) -> str:
    return value.strip().lower()


def normalize_phone(value: str) -> str:
    raw = value.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if raw.startswith("00"):
        raw = f"+{raw[2:]}"
    if raw.startswith("8") and len(raw) == 11:
        raw = f"+7{raw[1:]}"
    if not raw.startswith("+"):
        raw = f"+{raw}"
    return raw


def is_phone(value: str) -> bool:
    return bool(PHONE_REGEX.match(value))


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def needs_rehash(hashed_password: str) -> bool:
    return pwd_context.needs_update(hashed_password)


def create_token_pair(user_id: int, role: str) -> tuple[str, str]:
    now = datetime.now(timezone.utc)
    access_payload = {
        "sub": str(user_id),
        "role": role,
        "type": "access",
        "exp": int((now + timedelta(minutes=settings.access_token_ttl_minutes)).timestamp()),
        "iat": int(now.timestamp()),
    }
    refresh_payload = {
        "sub": str(user_id),
        "role": role,
        "type": "refresh",
        "exp": int((now + timedelta(days=settings.refresh_token_ttl_days)).timestamp()),
        "iat": int(now.timestamp()),
    }

    access_token = jwt.encode(access_payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    refresh_token = jwt.encode(refresh_payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return access_token, refresh_token


def decode_token(token: str, expected_type: str) -> dict:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise ValueError("Invalid token") from exc

    if payload.get("type") != expected_type:
        raise ValueError(f"Invalid token type: expected {expected_type}")
    return payload
