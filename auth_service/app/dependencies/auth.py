from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Annotated

from app.db_depends import get_db
from app.models.user import User
from app.routers.auth import get_current_user, oauth2_scheme


async def get_admin_user(
        db: Annotated[AsyncSession, Depends(get_db)],
        current_user: dict = Depends(get_current_user)
) -> dict:

    if current_user.get('role_id') != 68:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав. Требуется роль администратора"
        )

    return current_user