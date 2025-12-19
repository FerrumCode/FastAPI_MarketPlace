from fastapi import APIRouter, Depends, status, HTTPException, Body, Query, Request
from sqlalchemy import select, insert
from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordRequestForm
from datetime import datetime, timedelta
import jwt
import redis.asyncio as redis
from loguru import logger

from app.models.user import User
from app.models.role import Role
from app.schemas.user import CreateUser
from app.db_depends import get_db
from app.core.redis import get_redis
from app.dependencies.depend import (
    permission_required,
    ensure_refresh_token_not_blacklisted,
    authentication_and_get_current_user,
)
from app.utils import (
    create_access_token,
    create_refresh_token,
    authenticate_user,
)
from env import (
    SECRET_KEY,
    ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)

router = APIRouter(prefix="/auth", tags=["Auth"])
bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    db: Annotated[AsyncSession, Depends(get_db)],
    create_user: CreateUser,
):
    logger.info(
        "Attempt to register user with name '{name}' and email='{email}'",
        name=create_user.name,
        email=create_user.email,
    )

    try:
        result = await db.execute(select(Role).where(Role.name == "user"))
        role = result.scalar_one_or_none()

        if not role:
            logger.error(
                "Role 'user' not found during registration of user '{name}'",
                name=create_user.name,
            )
            raise HTTPException(status_code=527, detail="Role 'user' not found")

        await db.execute(
            insert(User).values(
                name=create_user.name,
                email=create_user.email,
                password_hash=bcrypt_context.hash(create_user.password),
                role_id=role.id,
            )
        )
        await db.commit()

        logger.info(
            "User '{name}' successfully registered with role id={role_id}",
            name=create_user.name,
            role_id=role.id,
        )
        return {"status_code": status.HTTP_201_CREATED, "transaction": "Successful"}

    except HTTPException:
        raise
    except Exception:
        raise


@router.post("/login")
async def login(
    db: Annotated[AsyncSession, Depends(get_db)],
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    redis_client: redis.Redis = Depends(get_redis),
):
    logger.info("Login attempt for user '{username}'", username=form_data.username)

    try:
        user = await authenticate_user(db, form_data.username, form_data.password)

        access_token = await create_access_token(
            user.name,
            user.id,
            user.role_id,
            timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        )
        refresh_token = await create_refresh_token(
            user.id,
            user.name,
            user.role_id,
            redis_client,
        )

        logger.info(
            "User '{username}' successfully logged in. user_id={user_id}, role_id={role_id}",
            username=user.name,
            user_id=user.id,
            role_id=user.role_id,
        )
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }

    except HTTPException:
        raise
    except Exception:
        raise


@router.get("/me", dependencies=[Depends(permission_required("can_me"))])
async def me(
    request: Request,
    redis_client: Annotated[redis.Redis, Depends(get_redis)],
    user: dict = Depends(authentication_and_get_current_user),
):
    logger.info(
        "Request for current user info /auth/me. user_id={user_id}, name='{name}'",
        user_id=user.get("id"),
        name=user.get("name"),
    )

    auth_header = request.headers.get("authorization")
    if not auth_header or not auth_header.lower().startswith("bearer "):
        logger.warning(
            "Request /auth/me without a valid Authorization header. path='{path}'",
            path=str(request.url.path),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing or invalid",
        )

    access_token = auth_header.split(" ", 1)[1].strip()

    stored_refresh = await redis_client.get(f"refresh_{user['id']}")
    if stored_refresh is None:
        logger.warning(
            "Refresh token for user_id={user_id} not found or revoked",
            user_id=user.get("id"),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found or revoked",
        )

    refresh_token = stored_refresh.decode() if isinstance(stored_refresh, bytes) else stored_refresh

    logger.info("Successful /auth/me response for user_id={user_id}", user_id=user.get("id"))
    return {
        "name": user["name"],
        "id": user["id"],
        "role_id": user["role_id"],
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.post(
    "/refresh",
    dependencies=[
        Depends(ensure_refresh_token_not_blacklisted),
        Depends(permission_required("can_refresh")),
    ],
)
async def refresh(
    refresh_token: Annotated[str, Body(embed=True)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis_client: Annotated[redis.Redis, Depends(get_redis)],
):
    logger.info("Attempt to refresh access token using refresh token")

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        user_id: str = payload.get("id")
        role_id: int = payload.get("role_id")

        if not username or not user_id:
            logger.error("Failed to extract user data from refresh token during refresh")
            raise credentials_exception

        result = await db.execute(select(User).where(User.name == username))
        user = result.scalar_one_or_none()
        if user is None:
            logger.warning("User '{username}' not found during token refresh", username=username)
            raise credentials_exception

        stored_refresh = await redis_client.get(f"refresh_{user_id}")
        if stored_refresh is None:
            logger.warning(
                "Refresh token for user_id={user_id} not found in Redis during refresh",
                user_id=user_id,
            )
            raise credentials_exception

        if isinstance(stored_refresh, bytes):
            stored_refresh = stored_refresh.decode()

        if stored_refresh != refresh_token:
            logger.warning(
                "Refresh token from request does not match token in Redis for user_id={user_id}",
                user_id=user_id,
            )
            raise credentials_exception

        access_token = await create_access_token(
            username,
            user_id,
            role_id,
            timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        )
        new_refresh_token = await create_refresh_token(
            user_id,
            username,
            role_id,
            redis_client,
        )

        logger.info(
            "Successfully refreshed tokens for user '{username}' (user_id={user_id})",
            username=username,
            user_id=user_id,
        )
        return {
            "access_token": access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
        }

    except jwt.ExpiredSignatureError:
        logger.warning("Refresh token expired during refresh attempt")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token expired",
        )
    except jwt.InvalidTokenError:
        logger.error("Invalid refresh token during refresh attempt")
        raise credentials_exception


@router.post(
    "/blacklisting",
    dependencies=[Depends(permission_required("can_blacklisting"))],
)
async def blacklisting(
    refresh_token: Annotated[str, Body(embed=True)],
    redis_client: Annotated[redis.Redis, Depends(get_redis)],
):
    logger.info("Attempt to add refresh token to blacklist")

    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        exp = payload.get("exp")
        ttl = exp - int(datetime.utcnow().timestamp())

        if ttl > 0:
            await redis_client.setex(f"bl_refresh_{refresh_token}", ttl, "true")
            logger.info("Refresh token added to blacklist with TTL={ttl} seconds", ttl=ttl)
    except jwt.InvalidTokenError:
        logger.warning("Attempt to add invalid refresh token to blacklist")
        pass

    return {"detail": "Refresh token blacklisted successfully"}


@router.get(
    "/blacklist",
    dependencies=[Depends(permission_required("can_blacklist"))],
)
async def blacklist(
    redis_client: Annotated[redis.Redis, Depends(get_redis)],
    prefix: str = Query("bl_refresh_", description="Prefix for blacklist keys"),
):
    logger.info("Request for blacklist tokens list with prefix '{prefix}'", prefix=prefix)

    keys = await redis_client.keys(f"{prefix}*")
    tokens = [key.decode().replace(prefix, "") for key in keys]

    logger.info(
        "Found {count} token(s) in blacklist with prefix '{prefix}'",
        count=len(tokens),
        prefix=prefix,
    )
    return {"blacklist": tokens}


@router.delete(
    "/blacklist/remove",
    dependencies=[Depends(permission_required("can_remove"))],
)
async def remove(
    refresh_token: Annotated[str, Body(embed=True)],
    redis_client: Annotated[redis.Redis, Depends(get_redis)],
):
    logger.info("Attempt to remove refresh token from blacklist")

    deleted = await redis_client.delete(f"bl_refresh_{refresh_token}")
    if deleted == 0:
        logger.info("Attempt to remove refresh token that is not in blacklist")
        return {"detail": "Token not found in blacklist"}

    logger.info("Refresh token successfully removed from blacklist")
    return {"detail": "Token removed from blacklist"}
