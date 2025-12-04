from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated

from loguru import logger

from app.db_depends import get_db
from app.schemas.permission import CreatePermission
from app.crud.permissions import (
    get_permission_from_db,
    create_permission_in_db,
    change_permission_in_db,
    delete_permission_in_db,
)
from app.dependencies.depend import permission_required


router = APIRouter(prefix="/permission", tags=["Permission"])


@router.get(
    "/",
    dependencies=[Depends(permission_required("can_get_permissions"))],
)
async def get_permission(
    db: Annotated[AsyncSession, Depends(get_db)],
    id: int | None = None,
    code: str | None = None,
):
    logger.info("GET /permission called with id={id}, code={code}", id=id, code=code)
    permission = await get_permission_from_db(db, permission_id=id, code=code)
    logger.info(
        "GET /permission successfully returned permission with id={id} and code={code}",
        id=getattr(permission, "id", None),
        code=getattr(permission, "code", None),
    )
    return permission


@router.post(
    "/",
    dependencies=[Depends(permission_required("can_create_permission"))],
    status_code=status.HTTP_201_CREATED,
)
async def create_permission(
    db: Annotated[AsyncSession, Depends(get_db)],
    new_permission: CreatePermission,
):
    logger.info(
        "POST /permission called to create permission with code={code}",
        code=new_permission.code,
    )
    result = await create_permission_in_db(db, new_permission)
    logger.info(
        "POST /permission successfully created permission with code={code}",
        code=result["permission"].code,
    )
    return result


@router.put(
    "/{permission_code}",
    dependencies=[Depends(permission_required("can_change_permission"))],
    status_code=status.HTTP_200_OK,
)
async def change_permission(
    db: Annotated[AsyncSession, Depends(get_db)],
    permission_code: str,
    permission_data: CreatePermission,
):
    logger.info(
        "PUT /permission/{permission_code} called to update permission. New code={new_code}",
        permission_code=permission_code,
        new_code=permission_data.code,
    )
    result = await change_permission_in_db(db, permission_code, permission_data)
    logger.info(
        "PUT /permission/{permission_code} successfully updated permission to code={new_code}",
        permission_code=permission_code,
        new_code=result["new_code"],
    )
    return result


@router.delete(
    "/{code}",
    dependencies=[Depends(permission_required("can_delete_permission"))],
)
async def delete_permission(
    db: Annotated[AsyncSession, Depends(get_db)],
    code: str,
):
    logger.info(
        "DELETE /permission/{code} called to delete permission", code=code
    )
    result = await delete_permission_in_db(db, code)
    logger.info(
        "DELETE /permission/{code} successfully deleted permission", code=code
    )
    return result
