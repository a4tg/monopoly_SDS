from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.core.tokens import TOKEN_ASSETS
from app.db.base import Base
from app.db.session import engine
from app.models import SecretShopItem, User, UserRole


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def seed_demo_data(db: Session) -> None:
    has_users = db.execute(select(User.id)).first()
    if not has_users:
        db.add_all(
            [
                User(email="admin@demo.local", phone="+79990000001", password=hash_password("admin"), role=UserRole.ADMIN),
                User(
                    email="player@demo.local",
                    phone="+79990000002",
                    password=hash_password("player"),
                    role=UserRole.PLAYER,
                    token_asset=TOKEN_ASSETS[1],
                ),
            ]
        )

    has_shop = db.execute(select(SecretShopItem.id)).first()
    if not has_shop:
        db.add_all(
            [
                SecretShopItem(name="Coffee coupon", price_points=20, stock=500, is_active=1),
                SecretShopItem(name="Notebook", price_points=35, stock=300, is_active=1),
                SecretShopItem(name="Sticker pack", price_points=10, stock=1000, is_active=1),
            ]
        )

    db.commit()
