from typing import Any, Dict
from uuid import UUID

import jwt  # PyJWT
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette import status

from app.core.config import settings

# будем переиспользовать и в роутере, чтобы достать сам Bearer токен
http_bearer = HTTPBearer(auto_error=True)


async def get_current_user(
    creds: HTTPAuthorizationCredentials = Security(http_bearer),
) -> Dict[str, Any]:
    token = creds.credentials
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options={"require": ["exp"]},
        )
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

    if "id" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload missing 'id'",
        )

    # ВАЖНО: предполагаем, что в токене есть role_id
    # (его должен проставлять Auth Service при выдаче access-токена)
    if "role_id" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload missing 'role_id'",
        )

    return payload


def can_access_order(current_user: Dict[str, Any], order_user_id: UUID) -> None:
    # проверяем, что текущий юзер валиден
    try:
        current_user_uuid = (
            current_user["id"]
            if isinstance(current_user["id"], UUID)
            else UUID(str(current_user["id"]))
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user id in token",
        )

    user_role_id = current_user.get("role_id")
    user_is_admin = (user_role_id == 1)
    user_is_owner = (current_user_uuid == order_user_id)

    if not user_is_admin and not user_is_owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to access this order",
        )
