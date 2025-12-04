from fastapi import HTTPException, status
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from loguru import logger

from app.models.permission import Permission
from app.schemas.permission import CreatePermission


async def get_permission_from_db(
    db: AsyncSession,
    permission_id: int | None = None,
    code: str | None = None,
):
    logger.info(
        "Requesting permission from DB with parameters: id={permission_id}, code={code}",
        permission_id=permission_id,
        code=code,
    )

    if (permission_id is None and code is None) or (
        permission_id is not None and code is not None
    ):
        logger.error(
            "Invalid combination of parameters in get_permission_from_db: permission_id={permission_id}, code={code}",
            permission_id=permission_id,
            code=code,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Specify exactly one parameter: either id or code.",
        )

    try:
        if permission_id is not None:
            result = await db.execute(
                select(Permission).where(Permission.id == permission_id)
            )
            ident = f"id={permission_id}"
        else:
            result = await db.execute(
                select(Permission).where(Permission.code == code)
            )
            ident = f"code='{code}'"

        permission = result.scalar_one_or_none()

        if not permission:
            logger.warning(
                "Permission not found in DB by {ident}",
                ident=ident
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Permission with {ident} not found",
            )

        logger.info(
            "Permission successfully retrieved from DB: id={id}, code={code}",
            id=permission.id,
            code=permission.code,
        )
        return permission

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            "Unexpected error while retrieving permission from DB"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error while retrieving permission: {str(e)}",
        )


async def create_permission_in_db(
    db: AsyncSession,
    create_permission: CreatePermission,
):
    logger.info(
        "Attempt to create a new permission with code='{code}'",
        code=create_permission.code,
    )

    try:
        result = await db.execute(
            select(Permission).where(Permission.code == create_permission.code)
        )
        existing_permission = result.scalar_one_or_none()

        if existing_permission:
            logger.warning(
                "Attempt to create an already existing permission with code='{code}'",
                code=create_permission.code,
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Permission with code '{create_permission.code}' already exists",
            )

        new_permission = Permission(
            code=create_permission.code,
            description=create_permission.description,
        )

        db.add(new_permission)
        await db.commit()
        await db.refresh(new_permission)

        logger.info(
            "Permission successfully created in DB: id={id}, code={code}",
            id=new_permission.id,
            code=new_permission.code,
        )

        return {
            "status_code": status.HTTP_201_CREATED,
            "message": "Permission successfully created",
            "permission": new_permission,
        }

    except HTTPException:
        logger.warning(
            "HTTPException occurred while creating permission in DB"
        )
        await db.rollback()
        raise
    except Exception as e:
        logger.exception("Unexpected error while creating permission in DB")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error while creating permission: {str(e)}",
        )


async def change_permission_in_db(
    db: AsyncSession,
    permission_code: str,
    permission_data: CreatePermission,
):
    logger.info(
        "Attempt to update permission with code='{code}'. New code='{new_code}'",
        code=permission_code,
        new_code=permission_data.code,
    )

    try:
        result = await db.execute(
            select(Permission).where(Permission.code == permission_code)
        )
        permission = result.scalar_one_or_none()

        if not permission:
            logger.warning(
                "Attempt to update non-existent permission with code='{code}'",
                code=permission_code,
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Permission with code '{permission_code}' not found",
            )

        if permission_data.code != permission_code:
            logger.debug(
                "Checking code conflict when changing code from '{old_code}' to '{new_code}'",
                old_code=permission_code,
                new_code=permission_data.code,
            )
            result = await db.execute(
                select(Permission).where(Permission.code == permission_data.code)
            )
            existing_permission = result.scalar_one_or_none()

            if existing_permission:
                logger.warning(
                    "Attempt to change permission code to an already existing code='{code}'",
                    code=permission_data.code,
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Permission with code '{permission_data.code}' already exists",
                )

        await db.execute(
            update(Permission)
            .where(Permission.code == permission_code)
            .values(
                code=permission_data.code,
                description=permission_data.description,
            )
        )
        await db.commit()

        logger.info(
            "Permission successfully updated in DB: old_code='{old_code}', new_code='{new_code}'",
            old_code=permission_code,
            new_code=permission_data.code,
        )

        return {
            "status": "success",
            "message": "Permission successfully updated",
            "old_code": permission_code,
            "new_code": permission_data.code,
            "new_description": permission_data.description,
        }

    except HTTPException:
        logger.warning(
            "HTTPException occurred while updating permission in DB"
        )
        await db.rollback()
        raise
    except Exception as e:
        logger.exception("Unexpected error while updating permission in DB")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error while updating permission: {str(e)}",
        )


async def delete_permission_in_db(db: AsyncSession, code: str):
    logger.info(
        "Attempt to delete permission with code='{code}' from DB",
        code=code,
    )

    try:
        permission_result = await db.execute(
            select(Permission).where(Permission.code == code)
        )
        permission = permission_result.scalar_one_or_none()

        if not permission:
            logger.warning(
                "Attempt to delete non-existent permission with code='{code}'",
                code=code,
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Permission with code '{code}' not found",
            )

        await db.execute(delete(Permission).where(Permission.code == code))
        await db.commit()

        logger.info(
            "Permission with code='{code}' successfully deleted from DB",
            code=code,
        )

        return {
            "status_code": status.HTTP_200_OK,
            "message": "Permission successfully deleted",
        }

    except HTTPException:
        logger.warning(
            "HTTPException occurred while deleting permission from DB"
        )
        await db.rollback()
        raise
    except Exception as e:
        logger.exception("Unexpected error while deleting permission from DB")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error while deleting permission: {str(e)}",
        )
