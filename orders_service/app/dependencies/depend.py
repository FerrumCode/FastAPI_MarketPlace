from typing import Any, Dict
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from env import SECRET_KEY, ALGORITHM

from sqlalchemy.ext.asyncio import AsyncSession
from app.db_depends import get_db
from app.service.orders import get_order as svc_get_order


bearer_scheme = HTTPBearer()


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


def permission_required(required_permission: str):
    def _checker(user=Depends(authentication_get_current_user)):
        perms = user.get("permissions") or []
        if required_permission not in perms:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{required_permission}' required"
            )
        return True
    return _checker


async def user_owner_access_checker(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(authentication_get_current_user),
) -> None:
    role_name = (current_user.get("role_name") or "").strip().lower()
    if role_name != "user":
        return

    user_uuid = UUID(str(current_user["id"]))
    order = await svc_get_order(db, order_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    if order.user_id != user_uuid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to access this order (owner only, role 'user')",
        )
