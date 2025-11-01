from fastapi import APIRouter, Depends, status, HTTPException, Body, Query
from sqlalchemy import select, insert, text
from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from datetime import datetime, timedelta
import jwt
import redis.asyncio as redis

from app.models.user import User
from app.models.role import Role
from app.schemas.user import CreateUser
from app.db_depends import get_db
from app.core.redis import get_redis
from env import SECRET_KEY, ALGORITHM




ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")
router = APIRouter(prefix='/auth', tags=['Auth'])
bcrypt_context = CryptContext(schemes=['bcrypt'], deprecated='auto')


# =======================
# Permissions helper
# =======================
async def fetch_permissions_by_role_id(db: AsyncSession, role_id: int) -> list[str]:
    """
    Возвращает список кодов пермитов для роли (permissions.code) по role_id.
    Используется таблица связей roles_permissions (role_id, permission_id).
    """
    # Явный SQL, чтобы не зависеть от наличия модели association table.
    res = await db.execute(
        text(
            """
            SELECT p.code
            FROM permissions AS p
            JOIN roles_permissions AS rp ON rp.permission_id = p.id
            WHERE rp.role_id = :role_id
            ORDER BY p.code
            """
        ),
        {"role_id": role_id},
    )
    rows = res.fetchall()
    return [row[0] for row in rows]


# =======================
# JWT Token Helpers
# =======================
async def create_access_token(username: str, user_id: int, role_id: int, expires_delta: timedelta):
    """
    Создает access-токен и ДОБАВЛЯЕТ в него permissions роли.
    Сигнатуру не меняем (чтобы не трогать эндпоинты) — сессию БД берём сами.
    """
    # 1) Получаем пермиты роли
    permissions: list[str] = []
    try:
        # используем dependency как генератор
        async for db in get_db():
            permissions = await fetch_permissions_by_role_id(db, role_id)
            break
    except Exception:
        # fail-closed — если что-то пошло не так, токен просто без пермитов
        permissions = []

    # 2) Формируем payload
    expire = datetime.utcnow() + expires_delta
    payload = {
        'sub': username,
        'id': str(user_id),
        'role_id': role_id,
        'permissions': permissions,  # <-- массив кодов пермитов
        'exp': int(expire.timestamp()),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


async def create_refresh_token(user_id: int, username: str, role_id: int, redis_client: redis.Redis):
    """Создает refresh token и сохраняет его в Redis (без пермитов — как и просил)."""
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
async def authenticate_user(db: Annotated[AsyncSession, Depends(get_db)],
                            username: str,
                            password: str):
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
async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)],
                           redis_client: redis.Redis = Depends(get_redis),
                           db: Annotated[AsyncSession, Depends(get_db)] = None):
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
        permissions: list[str] | None = payload.get('permissions')

        if username is None or user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Could not validate user'
            )

        # Обратная совместимость: если старый токен без permissions — дотянем их из БД
        if permissions is None and db is not None and role_id is not None:
            try:
                permissions = await fetch_permissions_by_role_id(db, role_id)
            except Exception:
                permissions = []

        return {'name': username, 'id': user_id, 'role_id': role_id, 'permissions': permissions or []}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired!")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Could not validate user')


# =======================
# Auth Routes
# =======================
@router.post('/register',
             status_code=status.HTTP_201_CREATED)
async def register(db: Annotated[AsyncSession, Depends(get_db)],
                   create_user: CreateUser):
    """Регистрация нового пользователя"""
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
async def login(db: Annotated[AsyncSession, Depends(get_db)],
                form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
                redis_client: redis.Redis = Depends(get_redis)):
    """Авторизация пользователя и выдача токенов"""
    user = await authenticate_user(db, form_data.username, form_data.password)

    access_token = await create_access_token(
        user.name, user.id, user.role_id, timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    refresh_token = await create_refresh_token(user.id, user.name, user.role_id, redis_client)

    return {'access_token': access_token, 'refresh_token': refresh_token, 'token_type': 'bearer'}


@router.get('/me')
async def me(redis_client: Annotated[redis.Redis, Depends(get_redis)],
             user: dict = Depends(get_current_user)):
    """Выдает новый access-токен.Refresh-токен берется из Redis (существующий), без перевыдачи."""
    # 1. Генерим новый access token
    access_token = await create_access_token(
        username=user['name'],
        user_id=user['id'],
        role_id=user['role_id'],
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    # 2. Достаём существующий refresh token из Redis
    stored_refresh = await redis_client.get(f"refresh_{user['id']}")

    if stored_refresh is None:
        # нет валидного refresh токена в Redis
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found or revoked"
        )

    # redis возвращает bytes — конвертируем в str при необходимости
    if isinstance(stored_refresh, bytes):
        refresh_token = stored_refresh.decode()
    else:
        refresh_token = stored_refresh

    return {
        "name": user["name"],
        "id": user["id"],
        "role_id": user["role_id"],
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.post("/refresh")
async def refresh(refresh_token: Annotated[str, Body(embed=True)],
                  db: Annotated[AsyncSession, Depends(get_db)],
                  redis_client: Annotated[redis.Redis, Depends(get_redis)]):
    """Обновление access и refresh токенов"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        if await redis_client.get(f"bl_refresh_{refresh_token}"):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token has been revoked")

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
        if stored_refresh is None:
            raise credentials_exception

        if isinstance(stored_refresh, bytes):
            stored_refresh = stored_refresh.decode()
        if stored_refresh != refresh_token:
            raise credentials_exception

        access_token = await create_access_token(username, user_id, role_id, timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
        new_refresh_token = await create_refresh_token(user_id, username, role_id, redis_client)

        return {'access_token': access_token, 'refresh_token': new_refresh_token, 'token_type': 'bearer'}

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired")
    except jwt.InvalidTokenError:
        raise credentials_exception


@router.post("/blacklisting")
async def blacklisting(refresh_token: Annotated[str, Body(embed=True)],
                       redis_client: Annotated[redis.Redis, Depends(get_redis)]):
    """Добавление refresh-токена в blacklist"""
    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        exp = payload.get("exp")
        ttl = exp - int(datetime.utcnow().timestamp())
        if ttl > 0:
            await redis_client.setex(f"bl_refresh_{refresh_token}", ttl, "true")
    except jwt.InvalidTokenError:
        pass
    return {"detail": "Refresh token blacklisted successfully"}


@router.get("/blacklist")
async def blacklist(redis_client: Annotated[redis.Redis, Depends(get_redis)],
                    prefix: str = Query("bl_refresh_",
                    description="Префикс для ключей blacklist")):
    """Посмотреть список refresh-токены, находящиеся в blacklist"""
    keys = await redis_client.keys(f"{prefix}*")
    tokens = [key.decode().replace(prefix, "") for key in keys]
    return {"blacklist": tokens}


@router.delete("/blacklist/remove")
async def remove(refresh_token: Annotated[str, Body(embed=True)],
                 redis_client: Annotated[redis.Redis, Depends(get_redis)]):
    """Удалить refresh-токен из blacklist"""
    deleted = await redis_client.delete(f"bl_refresh_{refresh_token}")
    if deleted == 0:
        return {"detail": "Token not found in blacklist"}
    return {"detail": "Token removed from blacklist"}
