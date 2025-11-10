from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated

from app.db_depends import get_db
from app.schemas.permission import CreatePermission
from app.crud.permissions import (
    get_permission_from_db,   # новый импорт
    create_permission_in_db,
    change_permission_in_db,
    delete_permission_in_db,
)
from app.dependencies.depend import permission_required


router = APIRouter(prefix="/permission", tags=["Permission"])


@router.get("/",
            dependencies=[Depends(permission_required("can_get_permissions"))])
async def get_permission(
    db: Annotated[AsyncSession, Depends(get_db)],
    id: int | None = None,
    code: str | None = None,
):
    return await get_permission_from_db(db, permission_id=id, code=code)


@router.post("/",
             dependencies=[Depends(permission_required("can_create_permission"))],
             status_code=status.HTTP_201_CREATED)
async def create_permission(
    db: Annotated[AsyncSession, Depends(get_db)],
    new_permission: CreatePermission,
):
    return await create_permission_in_db(db, new_permission)


@router.put("/{permission_code}",
            dependencies=[Depends(permission_required("can_change_permission"))],
            status_code=status.HTTP_200_OK)
async def change_permission(
    db: Annotated[AsyncSession, Depends(get_db)],
    permission_code: str,
    permission_data: CreatePermission,
):
    return await change_permission_in_db(db, permission_code, permission_data)


@router.delete("/{code}",
               dependencies=[Depends(permission_required("can_delete_permission"))])
async def delete_permission(
    db: Annotated[AsyncSession, Depends(get_db)],
    code: str,
):
    return await delete_permission_in_db(db, code)
