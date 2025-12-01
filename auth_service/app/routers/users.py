from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated
from loguru import logger

from app.schemas.user import CreateUser, UpdateUser
from app.db_depends import get_db
from app.crud.users import (
    get_user_from_db,
    create_user_in_db,
    update_user_by_name as update_user_in_db,
    delete_user as delete_user_from_db,
)
from app.dependencies.depend import permission_required


router = APIRouter(prefix="/users", tags=["Users"])



@router.get(
    "/{name}",
    dependencies=[Depends(permission_required("can_get_user"))],
)
async def get_user(
    db: Annotated[AsyncSession, Depends(get_db)],
    name: str,
):
    logger.info(
        "Вызван endpoint GET /users/{name} для получения пользователя",
        name=name,
    )
    return await get_user_from_db(db, name)


@router.post(
    "/",
    dependencies=[Depends(permission_required("can_create_user"))],
    status_code=status.HTTP_201_CREATED,
)
async def create_user(
    db: Annotated[AsyncSession, Depends(get_db)],
    create_user_data: CreateUser,
    role_id: int,
):
    logger.info(
        "Вызван endpoint POST /users для создания пользователя '{name}' с ролью role_id={role_id}",
        name=create_user_data.name,
        role_id=role_id,
    )
    return await create_user_in_db(db, create_user_data, role_id)


@router.put(
    "/{name}",
    dependencies=[Depends(permission_required("can_update_user_by_name"))],
    status_code=200,
)
async def update_user_by_name(
    db: Annotated[AsyncSession, Depends(get_db)],
    name: str,
    update_user_data: UpdateUser,
    role_id: int,
):
    logger.info(
        "Вызван endpoint PUT /users/{name} для обновления пользователя. Новое имя='{new_name}', role_id={role_id}",
        name=name,
        new_name=update_user_data.name,
        role_id=role_id,
    )
    return await update_user_in_db(db, name, update_user_data, role_id)


@router.delete(
    "/{name}",
    dependencies=[Depends(permission_required("can_delete_user"))],
)
async def delete_user(
    db: Annotated[AsyncSession, Depends(get_db)],
    name: str,
):
    logger.info(
        "Вызван endpoint DELETE /users/{name} для удаления пользователя",
        name=name,
    )
    return await delete_user_from_db(db, name)
