from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated

from app.db_depends import get_db
from app.schemas.role import CreateRole
from app.dependencies.auth import verify_admin_and_get_user
from app.crud.roles import (
    get_roles_from_db,
    create_role_in_db,
    update_role_in_db,
    delete_role_from_db,
)


router = APIRouter(prefix="/role", tags=["Role"])


@router.get("/get_roles")
async def get_roles(
    db: Annotated[AsyncSession, Depends(get_db)],
    admin_user: dict = Depends(verify_admin_and_get_user)
):
    return await get_roles_from_db(db)


@router.post("/create_role", status_code=status.HTTP_201_CREATED)
async def create_role(
    db: Annotated[AsyncSession, Depends(get_db)],
    create_role_data: CreateRole,
    admin_user: dict = Depends(verify_admin_and_get_user)
):
    return await create_role_in_db(db, create_role_data)


@router.put("/update_role/{role_name}", status_code=status.HTTP_200_OK)
async def update_role(
    db: Annotated[AsyncSession, Depends(get_db)],
    role_name: str,
    role_data: CreateRole,
    admin_user: dict = Depends(verify_admin_and_get_user)
):
    return await update_role_in_db(db, role_name, role_data)


@router.delete("/delete_role/{name}")
async def delete_role(
    db: Annotated[AsyncSession, Depends(get_db)],
    name: str,
    admin_user: dict = Depends(verify_admin_and_get_user)
):
    return await delete_role_from_db(db, name)
