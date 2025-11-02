from typing import Any, Dict
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from env import SECRET_KEY, ALGORITHM


bearer_scheme = HTTPBearer()


# Аутентификация - для всех сервисов(кроме Auth) через токен HTTPBearer()
def authentication_get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return {
            "id": payload.get("id"),
            "name": payload.get("sub"),
            "role_id": payload.get("role_id"),
            "permissions": payload.get("permissions", []),
        }
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )


# Аутентификация + Авторизация
def permission_required(required_permission: str):
    """Проверка наличия точного пермита в токене"""
    def _checker(user = Depends(authentication_get_current_user)):
        perms = user.get("permissions") or []
        if required_permission not in perms:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{required_permission}' required"
            )
        return True
    return _checker


# can_access_order (логика доступа заказ/пользователь) для orders_service.
def can_access_order(current_user: Dict[str, Any], order_user_id: UUID) -> None:
    """проверка — ТОЛЬКО на владение. Админ попадёт по пермитам на уровне эндпоинта."""
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

    # только владелец может пройти эту проверку
    if current_user_uuid != order_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to access this order (owner only)",
        )
