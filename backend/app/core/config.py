import os


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class Settings:
    app_name: str = "Monopoly SDS"
    app_env: str = os.getenv("APP_ENV", "development")
    database_url: str = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/monopoly_sds")
    jwt_secret: str = os.getenv("JWT_SECRET", "change-me")
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    access_token_ttl_minutes: int = int(os.getenv("ACCESS_TOKEN_TTL_MINUTES", "60"))
    refresh_token_ttl_days: int = int(os.getenv("REFRESH_TOKEN_TTL_DAYS", "30"))
    app_timezone: str = os.getenv("APP_TIMEZONE", "Europe/Moscow")
    password_reset_ttl_minutes: int = int(os.getenv("PASSWORD_RESET_TTL_MINUTES", "60"))
    password_reset_link_base_url: str = os.getenv("PASSWORD_RESET_LINK_BASE_URL", "http://localhost:5175/auth/reset")
    seed_demo_data: bool = _as_bool(os.getenv("SEED_DEMO_DATA"), default=True)
    cors_origins: list[str] = (
        ["*"]
        if os.getenv("CORS_ORIGINS", "*").strip() == "*"
        else [x.strip() for x in os.getenv("CORS_ORIGINS", "").split(",") if x.strip()]
    )


settings = Settings()
