from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated
from redis.asyncio import Redis
import hashlib

from app.db_depends import get_db
from app.models.user import User  # Используем SQLAlchemy модель User
from app.models.role import Role
from sqlalchemy import select
from app.routers.auth import get_current_user, oauth2_scheme

# -----------------------------
# Подключение к Redis (один экземпляр)
# -----------------------------
redis: Redis | None = None

async def get_redis() -> Redis:
    global redis
    if not redis:
        redis = Redis.from_url("redis://auth_redis:6379", decode_responses=True)
    return redis


# -----------------------------
# Зависимость: проверка прав администратора
# -----------------------------
async def  verify_admin_and_get_user(
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: dict = Depends(get_current_user)
) -> dict:
    result = await db.execute(select(Role).where(Role.id == current_user["role_id"]))
    role = result.scalar_one_or_none()

    if not role or role.name != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав. Требуется роль администратора"
        )
    return current_user


# -----------------------------
# Зависимость: проверка токена в blacklist
# -----------------------------
async def check_blacklist(
        token: str = Depends(oauth2_scheme),
        redis: Redis = Depends(get_redis)
) -> str:
    # Используем хэш токена для ключа в Redis
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    is_blacklisted = await redis.get(f"bl_{token_hash}")

    if is_blacklisted:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token revoked"
        )
    return token