from typing import Any, Dict

import httpx
from fastapi import Depends, HTTPException, Header
from starlette import status

from app.core.config import settings


async def get_current_user(authorization: str = Header(default=None)) -> Dict[str, Any]:
    """
    Прокси-проверка токена через Auth Service: /auth/me.
    Ожидает 'Authorization: Bearer <token>'.
    Возвращает dict пользователя (как даёт Auth).
    """
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Authorization header")

    async with httpx.AsyncClient(base_url=settings.AUTH_SERVICE_URL, timeout=5) as client:
        r = await client.get("/auth/me", headers={"Authorization": authorization})
        if r.status_code != 200:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
        return r.json()
