from typing import Any, Dict
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from env import SECRET_KEY, ALGORITHM

# --- добавлено для зависимости проверки владельца ---
from sqlalchemy.ext.asyncio import AsyncSession
from app.db_depends import get_db
from app.service.orders import get_order as svc_get_order
# ----------------------------------------------------

bearer_scheme = HTTPBearer()


# Аутентификация - для всех сервисов(кроме Auth) через токен HTTPBearer()
def authentication_get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)
):
    token = credentials.credentials
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
    def _checker(user=Depends(authentication_get_current_user)):
        perms = user.get("permissions") or []
        if required_permission not in perms:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{required_permission}' required"
            )
        return True
    return _checker


# Зависимость: проверка доступа владельца для роли 'user'. При нарушении прав/отсутствии заказа бросает HTTPException.
async def user_owner_access_checker(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(authentication_get_current_user),
) -> None:
    role_name = (current_user.get("role_name") or "").strip().lower()
    if role_name != "user":
        return  # доступ разрешён без доп. проверок для не-'user' ролей

    # Проверяем корректность UUID пользователя из токена
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

    # Получаем заказ и сверяем владельца
    order = await svc_get_order(db, order_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    if order.user_id != current_user_uuid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to access this order (owner only, role 'user')",
        )

    # return none, просто пропускаем дальше при успехе иначе проброс ошибки.
