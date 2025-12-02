from fastapi import HTTPException, status
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.models.role import Role
from app.schemas.role import CreateRole


async def get_role_from_db(
    db: AsyncSession,
    role_id: int | None = None,
    role_name: str | None = None,
):
    logger.info(
        "Request roles from DB: role_id={role_id}, role_name={role_name}",
        role_id=role_id,
        role_name=role_name,
    )
    try:
        if role_id is not None and role_name is not None:
            logger.warning(
                "Both parameters role_id and role_name are specified when requesting roles: "
                "role_id={role_id}, role_name={role_name}",
                role_id=role_id,
                role_name=role_name,
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Specify only one search parameter: either id or name.",
            )

        if role_id is not None:
            result = await db.execute(select(Role).where(Role.id == role_id))
            role = result.scalar_one_or_none()
            if not role:
                logger.warning(
                    "Role with id '{role_id}' not found when querying.",
                    role_id=role_id,
                )
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Role with id '{role_id}' not found",
                )
            logger.info("Role with id '{role_id}' successfully retrieved.", role_id=role_id)
            return role

        if role_name is not None:
            result = await db.execute(select(Role).where(Role.name == role_name))
            role = result.scalar_one_or_none()
            if not role:
                logger.warning(
                    "Role with name '{role_name}' not found when querying.",
                    role_name=role_name,
                )
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Role with name '{role_name}' not found",
                )
            logger.info(
                "Role with name '{role_name}' successfully retrieved.",
                role_name=role_name,
            )
            return role

        query = select(Role)
        result = await db.execute(query)
        roles = result.scalars().all()
        logger.info("Roles list obtained. Count: {count}", count=len(roles))
        return roles

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unhandled error while getting roles from DB")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error while getting roles: {str(e)}",
        )


async def create_role_in_db(db: AsyncSession, create_role: CreateRole):
    logger.info(
        "Attempt to create role with name '{name}'",
        name=create_role.name,
    )
    try:
        result = await db.execute(select(Role).where(Role.name == create_role.name))
        existing_role = result.scalar_one_or_none()

        if existing_role:
            logger.warning(
                "Attempt to create role with already existing name '{name}'",
                name=create_role.name,
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Role with name '{create_role.name}' already exists"
            )

        new_role = Role(
            name=create_role.name,
            description=create_role.description
        )

        db.add(new_role)
        await db.commit()
        await db.refresh(new_role)

        logger.info(
            "Role successfully created. id={id}, name='{name}'",
            id=new_role.id,
            name=new_role.name,
        )

        return {
            "status_code": status.HTTP_201_CREATED,
            "message": "Role successfully created",
            "role": new_role
        }

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.exception(
            "Unhandled error while creating role with name '{name}'",
            name=create_role.name,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error while creating role: {str(e)}"
        )


async def update_role_in_db(
    db: AsyncSession,
    role_name: str,
    role_data: CreateRole
):
    logger.info(
        "Attempt to update role: old name='{old_name}', new name='{new_name}'",
        old_name=role_name,
        new_name=role_data.name,
    )
    try:
        result = await db.execute(select(Role).where(Role.name == role_name))
        role = result.scalar_one_or_none()

        if not role:
            logger.warning(
                "Role with name '{role_name}' not found for update",
                role_name=role_name,
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Role with name '{role_name}' not found"
            )

        if role_data.name != role_name:
            result = await db.execute(select(Role).where(Role.name == role_data.name))
            existing_role = result.scalar_one_or_none()
            if existing_role:
                logger.warning(
                    "Attempt to rename role '{old_name}' to already existing name '{new_name}'",
                    old_name=role_name,
                    new_name=role_data.name,
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Role with name '{role_data.name}' already exists"
                )

        await db.execute(
            update(Role)
            .where(Role.name == role_name)
            .values(
                name=role_data.name,
                description=role_data.description
            )
        )
        await db.commit()

        logger.info(
            "Role successfully updated: old name='{old_name}', new name='{new_name}'",
            old_name=role_name,
            new_name=role_data.name,
        )

        return {
            "status": "success",
            "message": "Role successfully updated",
            "old_name": role_name,
            "new_name": role_data.name,
            "new_description": role_data.description,
        }

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.exception(
            "Unhandled error while updating role '{role_name}'",
            role_name=role_name,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error while updating role: {str(e)}"
        )


async def delete_role_from_db(db: AsyncSession, name: str):
    logger.info(
        "Attempt to delete role with name '{name}'",
        name=name,
    )
    result = await db.execute(select(Role).where(Role.name == name))
    role = result.scalar_one_or_none()

    if not role:
        logger.warning(
            "Role with name '{name}' not found for deletion",
            name=name,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role with name '{name}' not found"
        )

    await db.execute(delete(Role).where(Role.name == name))
    await db.commit()

    logger.info(
        "Role with name '{name}' successfully deleted",
        name=name,
    )

    return {
        "status_code": status.HTTP_200_OK,
        "transaction": "Role deleted successfully"
    }
