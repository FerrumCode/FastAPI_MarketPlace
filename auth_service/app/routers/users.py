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
from app.dependencies.depend import permission_required


router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/",
            dependencies=[Depends(permission_required("can_get_users"))])
async def get_users(
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await get_all_users(db)


@router.get("/{name}",
            dependencies=[Depends(permission_required("can_get_user_info"))])
async def get_user_info(
    db: Annotated[AsyncSession, Depends(get_db)],
    name: str,
):
    return await get_user(db, name)


@router.post("/",
             dependencies=[Depends(permission_required("can_create_user"))],
             status_code=status.HTTP_201_CREATED)
async def create_user(
    db: Annotated[AsyncSession, Depends(get_db)],
    create_user_data: CreateUser,
    role_id: int,
):
    return await create_user_in_db(db, create_user_data, role_id)


@router.put("/{name}",
            dependencies=[Depends(permission_required("can_update_user_by_name"))],
            status_code=200)
async def update_user_by_name(
    db: Annotated[AsyncSession, Depends(get_db)],
    name: str,
    update_user_data: UpdateUser,
    role_id: int,
):
    return await update_user_by_name(db, name, update_user_data, role_id)


@router.delete("/{name}",
               dependencies=[Depends(permission_required("can_delete_user"))])
async def delete_user(
    db: Annotated[AsyncSession, Depends(get_db)],
    name: str,
):
    return await delete_user(db, name)
