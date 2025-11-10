from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy import select
from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession
from passlib.context import CryptContext
from datetime import datetime, timedelta
import jwt
import redis.asyncio as redis

from app.models.user import User
from app.models.role import Role
from app.models.permission import Permission
from app.schemas.user import CreateUser
from app.db_depends import get_db
from app.core.redis import get_redis
from app.dependencies.depend import (
    ensure_refresh_token_not_blacklisted,
    authentication_and_get_current_user
)

from env import SECRET_KEY, ALGORITHM, REFRESH_TOKEN_EXPIRE_DAYS


router = APIRouter(prefix="/auth", tags=["Auth"])
bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def fetch_permissions_by_role_id(db: AsyncSession, role_id: int) -> list[str]:
    result = await db.execute(
        select(Permission.code)
        .join(Role.permissions)
        .where(Role.id == role_id)
        .order_by(Permission.code)
    )
    return list(result.scalars().all())


async def fetch_role_name_by_role_id(db: AsyncSession, role_id: int) -> str | None:
    res = await db.execute(select(Role.name).where(Role.id == role_id))
    return res.scalar_one_or_none()


async def create_access_token(
    username: str, user_id: int, role_id: int, expires_delta: timedelta
):
    permissions: list[str] = []
    role_name: str | None = None
    try:
        async for db in get_db():
            permissions = await fetch_permissions_by_role_id(db, role_id)
            role_name = await fetch_role_name_by_role_id(db, role_id)
            break
    except Exception:
        permissions = []
        role_name = None

    expire = datetime.utcnow() + expires_delta
    payload = {
        "sub": username,
        "id": str(user_id),
        "role_id": role_id,
        "role_name": role_name,
        "permissions": permissions,
        "exp": int(expire.timestamp()),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


async def create_refresh_token(
    user_id: int, username: str, role_id: int, redis_client: redis.Redis
):
    role_name: str | None = None
    try:
        async for db in get_db():
            role_name = await fetch_role_name_by_role_id(db, role_id)
            break
    except Exception:
        role_name = None

    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": username,
        "id": str(user_id),
        "role_id": role_id,
        "role_name": role_name,  # <--- добавлено
        "exp": int(expire.timestamp()),
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    await redis_client.setex(
        f"refresh_{user_id}", REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600, token
    )
    return token


async def authenticate_user(
    db: Annotated[AsyncSession, Depends(get_db)],
    username: str,
    password: str,
):
    user = await db.scalar(select(User).where(User.name == username))
    if not user or not bcrypt_context.verify(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user