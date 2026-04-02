from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError

from app.api.auth import router as auth_router
from app.api.game import router as game_router
from app.api.admin import router as admin_router
from app.core.config import settings
from app.db.init_db import seed_demo_data
from app.db.session import SessionLocal

app = FastAPI(title="Monopoly SDS API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(game_router, prefix="/game", tags=["game"])
app.include_router(admin_router, prefix="/admin", tags=["admin"])


@app.on_event("startup")
def startup() -> None:
    db = SessionLocal()
    try:
        if settings.seed_demo_data:
            seed_demo_data(db)
    except SQLAlchemyError as exc:
        raise RuntimeError("Database schema is not ready. Run Alembic migrations before starting API.") from exc
    finally:
        db.close()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
