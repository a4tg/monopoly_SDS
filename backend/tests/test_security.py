from app.core.security import (
    create_token_pair,
    decode_token,
    hash_password,
    is_phone,
    normalize_email,
    normalize_phone,
    verify_password,
)


def test_password_hash_and_verify() -> None:
    plain = "secret-pass-123"
    hashed = hash_password(plain)
    assert hashed != plain
    assert verify_password(plain, hashed)


def test_phone_normalization_and_validation() -> None:
    normalized = normalize_phone("8 (999) 123-45-67")
    assert normalized == "+79991234567"
    assert is_phone(normalized)
    assert normalize_email("  USER@DEMO.LOCAL ") == "user@demo.local"


def test_access_refresh_token_types() -> None:
    access, refresh = create_token_pair(user_id=42, role="player")
    access_payload = decode_token(access, expected_type="access")
    refresh_payload = decode_token(refresh, expected_type="refresh")
    assert access_payload["sub"] == "42"
    assert refresh_payload["sub"] == "42"
