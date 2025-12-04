from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated
from loguru import logger

from app.db_depends import get_db
from app.schemas.role import CreateRole
from app.crud.roles import (
    get_role_from_db,
    create_role_in_db,
    update_role_in_db,
    delete_role_from_db,
)
from app.dependencies.depend import permission_required


router = APIRouter(prefix="/role", tags=["Role"])


@router.get("/",
            dependencies=[Depends(permission_required("can_get_role"))])
async def get_role(
    db: Annotated[AsyncSession, Depends(get_db)],
    id: int | None = None,
    name: str | None = None,
):
    logger.info(
        "Endpoint GET /role called with parameters id={id}, name='{name}'",
        id=id,
        name=name,
    )
    return await get_role_from_db(db, role_id=id, role_name=name)


@router.post("/",
             dependencies=[Depends(permission_required("can_create_role"))],
             status_code=status.HTTP_201_CREATED)
async def create_role(
    db: Annotated[AsyncSession, Depends(get_db)],
    create_role_data: CreateRole,
):
    logger.info(
        "Endpoint POST /role called to create role with name '{name}'",
        name=create_role_data.name,
    )
    return await create_role_in_db(db, create_role_data)


@router.put("/{role_name}",
            dependencies=[Depends(permission_required("can_update_role"))],
            status_code=status.HTTP_200_OK)
async def update_role(
    db: Annotated[AsyncSession, Depends(get_db)],
    role_name: str,
    role_data: CreateRole,
):
    logger.info(
        "Endpoint PUT /role/{role_name} called to update role",
        role_name=role_name,
    )
    return await update_role_in_db(db, role_name, role_data)


@router.delete("/{name}",
               dependencies=[Depends(permission_required("can_delete_role"))])
async def delete_role(
    db: Annotated[AsyncSession, Depends(get_db)],
    name: str,
):
    logger.info(
        "Endpoint DELETE /role/{name} called to delete role",
        name=name,
    )
    return await delete_role_from_db(db, name)
