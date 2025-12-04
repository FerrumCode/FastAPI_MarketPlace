import jwt
from fastapi import Depends, HTTPException, status, Body
from fastapi.security import OAuth2PasswordBearer

import redis.asyncio as redis
from loguru import logger

from env import SECRET_KEY, ALGORITHM
from app.core.redis import get_redis


bearer_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def ensure_refresh_token_not_blacklisted(
    refresh_token: str = Body(embed=True),
    redis_client: redis.Redis = Depends(get_redis),
):
    logger.debug("Checking if provided refresh token is blacklisted")

    if await redis_client.get(f"bl_refresh_{refresh_token}"):
        logger.warning("Attempt to use blacklisted refresh token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has been revoked",
        )

    logger.debug("Refresh token is not blacklisted")
    return True


def authentication_and_get_current_user(token: str = Depends(bearer_scheme)):
    logger.debug("Authenticating user from access token")

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        user = {
            "id": payload.get("id"),
            "name": payload.get("sub"),
            "role_id": payload.get("role_id"),
            "role_name": payload.get("role_name"),
            "permissions": payload.get("permissions", []),
        }

        logger.info(
            "User authenticated: id={id}, name={name}, role_id={role_id}, role_name={role_name}",
            id=user["id"],
            name=user["name"],
            role_id=user["role_id"],
            role_name=user["role_name"],
        )

        return user

    except jwt.ExpiredSignatureError:
        logger.warning("Access token expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
        )
    except jwt.InvalidTokenError:
        logger.warning("Invalid access token received")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )


def permission_required(required_permission: str):
    def _checker(user=Depends(authentication_and_get_current_user)):
        perms = user.get("permissions") or []
        user_id = user.get("id")
        user_name = user.get("name")

        if required_permission not in perms:
            logger.warning(
                "Permission check failed: user_id={user_id}, user_name={user_name}, "
                "required_permission='{perm}', user_permissions={perms}",
                user_id=user_id,
                user_name=user_name,
                perm=required_permission,
                perms=perms,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{required_permission}' required",
            )

        logger.debug(
            "Permission check passed: user_id={user_id}, user_name={user_name}, permission='{perm}'",
            user_id=user_id,
            user_name=user_name,
            perm=required_permission,
        )
        return True

    return _checker
