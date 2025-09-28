from fastapi import APIRouter, Depends, status, HTTPException, Body
from sqlalchemy import select, insert
from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from datetime import datetime, timedelta
import jwt
import redis.asyncio as redis
from fastapi import Query

from app.models.user import User
from app.models.role import Role
from app.schemas.user import CreateUser
from app.db_depends import get_db
from app.core.redis import get_redis

from env import SECRET_KEY, ALGORITHM

# Настройки JWT
# SECRET_KEY = 'a21679097c1ba42e9bd06eea239cdc5bf19b249e87698625cba5e3572f005544'
# ALGORITHM = 'HS256'
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")
router = APIRouter(prefix='/auth', tags=['Auth'])
bcrypt_context = CryptContext(schemes=['bcrypt'], deprecated='auto')


# =======================
# JWT Token Helpers
# =======================
async def create_access_token(username: str, user_id: int, role_id: int, expires_delta: timedelta):
    payload = {
        'sub': username,
        'id': str(user_id),
        'role_id': role_id,
        'exp': datetime.utcnow() + expires_delta
    }
    payload['exp'] = int(payload['exp'].timestamp())
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


async def create_refresh_token(user_id: int, username: str, role_id: int, redis_client: redis.Redis):
    """
    Создает refresh token и сохраняет его в Redis
    """
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": username,
        "id": str(user_id),
        "role_id": role_id,
        "exp": int(expire.timestamp())
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    await redis_client.setex(f"refresh_{user_id}", REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600, token)
    return token


# =======================
# Authentication Helpers
# =======================
async def authenticate_user(db: Annotated[AsyncSession, Depends(get_db)], username: str, password: str):
    user = await db.scalar(select(User).where(User.name == username))
    if not user or not bcrypt_context.verify(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


# =======================
# Current User Dependency
# =======================
async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    redis_client: redis.Redis = Depends(get_redis)
):
    try:
        # Проверка blacklist в Redis
        if await redis_client.get(f"bl_{token}"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked"
            )

        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str | None = payload.get('sub')
        user_id: int | None = payload.get('id')
        role_id: int | None = payload.get('role_id')

        if username is None or user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Could not validate user'
            )

        return {
            'name': username,
            'id': user_id,
            'role_id': role_id,
        }
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired!"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Could not validate user'
        )


# =======================
# Routes
# =======================
@router.post('/register', status_code=status.HTTP_201_CREATED)
async def sign_up(db: Annotated[AsyncSession, Depends(get_db)], create_user: CreateUser):
    result = await db.execute(select(Role).where(Role.name == "user"))
    role = result.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=527, detail="Role 'user' not found")

    await db.execute(insert(User).values(
        name=create_user.name,
        email=create_user.email,
        password_hash=bcrypt_context.hash(create_user.password),
        role_id=role.id
    ))
    await db.commit()
    return {'status_code': status.HTTP_201_CREATED, 'transaction': 'Successful'}


@router.post('/login')
async def sign_in(
    db: Annotated[AsyncSession, Depends(get_db)],
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    redis_client: redis.Redis = Depends(get_redis)
):
    user = await authenticate_user(db, form_data.username, form_data.password)

    access_token = await create_access_token(
        user.name,
        user.id,
        user.role_id,
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    refresh_token = await create_refresh_token(
        user.id,
        user.name,
        user.role_id,
        redis_client  # Передаем redis_client как параметр
    )

    return {'access_token': access_token, 'refresh_token': refresh_token, 'token_type': 'bearer'}


@router.get('/me')
async def read_current_user(user: dict = Depends(get_current_user)):
    return user


@router.post("/refresh")
async def refresh_token(
    refresh_token: Annotated[str, Body(embed=True)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis_client: Annotated[redis.Redis, Depends(get_redis)]
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Проверка blacklist в Redis
        if await redis_client.get(f"bl_refresh_{refresh_token}"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has been revoked"
            )

        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get('sub')
        user_id: str = payload.get('id')
        role_id: int = payload.get('role_id')

        if not username or not user_id:
            raise credentials_exception

        result = await db.execute(select(User).where(User.name == username))
        user = result.scalar_one_or_none()
        if user is None:
            raise credentials_exception

        stored_refresh = await redis_client.get(f"refresh_{user_id}")
        if stored_refresh is None or stored_refresh != refresh_token:
            raise credentials_exception

        access_token = await create_access_token(
            username, user_id, role_id,
            expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        )

        new_refresh_token = await create_refresh_token(user_id, username, role_id, redis_client)

        return {
            'access_token': access_token,
            'refresh_token': new_refresh_token,
            'token_type': 'bearer'
        }

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired")
    except jwt.InvalidTokenError:
        raise credentials_exception


@router.post("/blacklisting")
async def blacklisting(
    refresh_token: Annotated[str, Body(embed=True)],
    redis_client: Annotated[redis.Redis, Depends(get_redis)]
):
    try:
        # Декодируем, чтобы получить срок жизни
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        exp = payload.get("exp")

        # TTL для Redis = оставшееся время жизни токена
        ttl = exp - int(datetime.utcnow().timestamp())
        if ttl > 0:
            await redis_client.setex(f"bl_refresh_{refresh_token}", ttl, "true")
    except jwt.InvalidTokenError:
        # Если токен невалидный — просто игнорируем
        pass

    return {"detail": "Refresh token blacklisted successfully"}


# =======================
# Admin: посмотреть blacklist
# =======================
@router.get("/blacklist")
async def get_blacklist(
    redis_client: Annotated[redis.Redis, Depends(get_redis)],
    prefix: str = Query("bl_refresh_", description="Префикс для ключей blacklist")
):
    """
    Возвращает список refresh-токенов, находящихся в blacklist.
    """
    keys = await redis_client.keys(f"{prefix}*")
    tokens = [key.decode().replace(prefix, "") for key in keys]

    return {"blacklist": tokens}


# =======================
# Admin: удалить refresh из blacklist
# =======================
@router.delete("/blacklist/remove")
async def remove_from_blacklist(
    refresh_token: Annotated[str, Body(embed=True)],
    redis_client: Annotated[redis.Redis, Depends(get_redis)]
):
    """
    Удаляет указанный refresh-токен из blacklist.
    """
    deleted = await redis_client.delete(f"bl_refresh_{refresh_token}")
    if deleted == 0:
        return {"detail": "Token not found in blacklist"}

    return {"detail": "Token removed from blacklist"}
