from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated

from app.schemas.user import CreateUser, UpdateUser
from app.db_depends import get_db
from app.crud.users import (
    get_all_users,
    get_user,
    create_user_in_db,
    update_user_by_name,
    delete_user,
)
from app.dependencies.auth import verify_admin_and_get_user, check_blacklist
from app.dependencies.depend import permission_required


router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/get_users",
            dependencies=[Depends(permission_required("can_get_users"))])
async def get_users(
    db: Annotated[AsyncSession, Depends(get_db)],
    admin_user: dict = Depends(verify_admin_and_get_user),
    token: str = Depends(check_blacklist),
):
    """Получить список всех пользователей (доступно только админу)"""
    return await get_all_users(db)


@router.get("/get_user_info/{name}",
            dependencies=[Depends(permission_required("can_get_user_info"))])
async def get_user_info(
    db: Annotated[AsyncSession, Depends(get_db)],
    name: str,
    admin_user: dict = Depends(verify_admin_and_get_user),
):
    """Получить информацию о пользователе по имени"""
    return await get_user(db, name)


@router.post("/create_user",
             dependencies=[Depends(permission_required("can_create_user"))],
             status_code=status.HTTP_201_CREATED)
async def create_user(
    db: Annotated[AsyncSession, Depends(get_db)],
    create_user_data: CreateUser,
    role_id: int,
    admin_user: dict = Depends(verify_admin_and_get_user),
):
    """Создать нового пользователя (админ-доступ)"""
    return await create_user_in_db(db, create_user_data, role_id)


@router.put("/update_user_by_name/{name}",
            dependencies=[Depends(permission_required("can_update_user_by_name"))],
            status_code=200)
async def update_user_by_name(
    db: Annotated[AsyncSession, Depends(get_db)],
    name: str,
    update_user_data: UpdateUser,
    role_id: int,
    admin_user: dict = Depends(verify_admin_and_get_user),
):
    """Обновить данные пользователя по имени (админ-доступ)"""
    return await update_user_by_name(db, name, update_user_data, role_id)


@router.delete("/delete_user/{name}",
               dependencies=[Depends(permission_required("can_delete_user"))])
async def delete_user(
    db: Annotated[AsyncSession, Depends(get_db)],
    name: str,
    admin_user: dict = Depends(verify_admin_and_get_user),
):
    """Удалить пользователя (админ-доступ)"""
    return await delete_user(db, name)
