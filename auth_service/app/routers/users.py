from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated

from app.schemas.user import CreateUser
from app.db_depends import get_db
from app.crud.users import get_all_users, get_user, create_user_in_db, update_user_by_name, delete_user
from app.dependencies.auth import verify_admin_and_get_user, check_blacklist

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/get_users")
async def get_users(
    db: Annotated[AsyncSession, Depends(get_db)],
    admin_user: dict = Depends(verify_admin_and_get_user),
    token: str = Depends(check_blacklist)
):
    return await get_all_users(db)


@router.get('/get_user_info/{name}')
async def get_user_info(
    db: Annotated[AsyncSession, Depends(get_db)],
    name: str,
    admin_user: dict = Depends(verify_admin_and_get_user)
):
    return await get_user(db, name)


@router.post('/create_user', status_code=status.HTTP_201_CREATED)
async def create_user(
    db: Annotated[AsyncSession, Depends(get_db)],
    create_user_data: CreateUser,
    role_id: int,
    admin_user: dict = Depends(verify_admin_and_get_user)
):
    return await create_user_in_db(db, create_user_data, role_id)


@router.put('/update_user_by_name/{name}', status_code=200)
async def update_user_by_name(
    db: Annotated[AsyncSession, Depends(get_db)],
    name: str,
    update_user: CreateUser,
    role_id: int,
    admin_user: dict = Depends(verify_admin_and_get_user)
):
    return await update_user_by_name(db, name, update_user, role_id)


@router.delete('/delete_user/{name}')
async def delete_user(
    db: Annotated[AsyncSession, Depends(get_db)],
    name: str,
    admin_user: dict = Depends(verify_admin_and_get_user)
):
    return await delete_user(db, name)