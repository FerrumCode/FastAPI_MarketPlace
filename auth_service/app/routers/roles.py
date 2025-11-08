from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated

from app.db_depends import get_db
from app.schemas.role import CreateRole
from app.crud.roles import (
    get_roles_from_db,
    create_role_in_db,
    update_role_in_db,
    delete_role_from_db,
)
from app.dependencies.depend import permission_required


router = APIRouter(prefix="/role", tags=["Role"])


@router.get("/",
            dependencies=[Depends(permission_required("can_get_roles"))])
async def get_roles(
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await get_roles_from_db(db)


@router.post("/",
             dependencies=[Depends(permission_required("can_create_role"))],
             status_code=status.HTTP_201_CREATED)
async def create_role(
    db: Annotated[AsyncSession, Depends(get_db)],
    create_role_data: CreateRole,
):
    return await create_role_in_db(db, create_role_data)


@router.put("/{role_name}",
            dependencies=[Depends(permission_required("can_update_role"))],
            status_code=status.HTTP_200_OK)
async def update_role(
    db: Annotated[AsyncSession, Depends(get_db)],
    role_name: str,
    role_data: CreateRole,
):
    return await update_role_in_db(db, role_name, role_data)


@router.delete("/{name}",
               dependencies=[Depends(permission_required("can_delete_role"))])
async def delete_role(
    db: Annotated[AsyncSession, Depends(get_db)],
    name: str,
):
    return await delete_role_from_db(db, name)
