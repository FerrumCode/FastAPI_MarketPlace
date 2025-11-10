import jwt
from fastapi import Depends, HTTPException, status, Body
from fastapi.security import OAuth2PasswordBearer

import redis.asyncio as redis

from env import SECRET_KEY, ALGORITHM
from app.core.redis import get_redis


bearer_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def ensure_refresh_token_not_blacklisted(
    refresh_token: str = Body(embed=True),
    redis_client: redis.Redis = Depends(get_redis),
):
    if await redis_client.get(f"bl_refresh_{refresh_token}"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has been revoked",
        )
    return True


def authentication_and_get_current_user(token: str = Depends(bearer_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return {
            "id": payload.get("id"),
            "name": payload.get("sub"),
            "role_id": payload.get("role_id"),
            "role_name": payload.get("role_name"),
            "permissions": payload.get("permissions", []),
        }
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )


def permission_required(required_permission: str):
    def _checker(user=Depends(authentication_and_get_current_user)):
        perms = user.get("permissions") or []
        if required_permission not in perms:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{required_permission}' required",
            )
        return True

    return _checker