from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy import select, update, delete
from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.permission import Permission
from app.schemas.permission import CreatePermission
from app.db_depends import get_db
from app.dependencies.auth import verify_admin_and_get_user
from app.crud.permissions import get_permissions_from_db, create_permission_in_db, change_permission_in_db, delete_permission_in_db

router = APIRouter(prefix='/permission', tags=['Permission'])


@router.get('/get_permissions')
async def get_permissions(
    db: Annotated[AsyncSession, Depends(get_db)],
    admin_user: dict = Depends(verify_admin_and_get_user)
):
    return await get_permissions_from_db(db)


@router.post('/create_permission', status_code=status.HTTP_201_CREATED)
async def create_permission(
    db: Annotated[AsyncSession, Depends(get_db)],
    new_permission: CreatePermission,
    admin_user: dict = Depends(verify_admin_and_get_user)
):
    return await create_permission_in_db(db, new_permission)


@router.put('/change_permission/{permission_code}', status_code=status.HTTP_200_OK)
async def change_permission(
    db: Annotated[AsyncSession, Depends(get_db)],
    permission_code: str,
    permission_data: CreatePermission,  # Схема с новыми данными
    admin_user: dict = Depends(verify_admin_and_get_user)
):
    return await change_permission_in_db(db, permission_code, permission_data)


@router.delete('/delete_permission')
async def delete_permission(
    db: Annotated[AsyncSession, Depends(get_db)],
    code: str,  # Удаляем по коду разрешения
    admin_user: dict = Depends(verify_admin_and_get_user)
):
    return await delete_permission_in_db(db, code)