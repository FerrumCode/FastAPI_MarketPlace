from fastapi import HTTPException, status
from sqlalchemy import select, insert, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from passlib.context import CryptContext
from loguru import logger

from app.models.user import User
from app.models.role import Role
from app.schemas.user import CreateUser


bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def get_user_from_db(db: AsyncSession, name: str):
    logger.info("Requesting user from DB by name '{name}'", name=name)
    try:
        query = select(User).where(User.name == name)
        result = await db.execute(query)
        user = result.scalar_one_or_none()

        if not user:
            logger.warning(
                "User with name '{name}' not found during request",
                name=name,
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with name '{name}' not found",
            )
        logger.info(
            "User with name '{name}' successfully retrieved from DB",
            name=name,
        )
        return user
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            "Unhandled error while searching for user with name '{name}'",
            name=name,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error while searching for user: {str(e)}",
        )


async def create_user_in_db(
    db: AsyncSession,
    create_user_data: CreateUser,
    role_id: int,
):
    logger.info(
        "Attempting to create user '{name}' with role_id={role_id}",
        name=create_user_data.name,
        role_id=role_id,
    )
    result = await db.execute(select(Role).where(Role.id == role_id))
    role = result.scalar_one_or_none()

    if not role:
        logger.warning(
            "Role with ID {role_id} not found when creating user '{name}'",
            role_id=role_id,
            name=create_user_data.name,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role with ID {role_id} not found",
        )

    await db.execute(
        insert(User).values(
            name=create_user_data.name,
            email=create_user_data.email,
            password_hash=bcrypt_context.hash(create_user_data.password),
            role_id=role_id,
        )
    )
    await db.commit()

    logger.info(
        "User '{name}' successfully created with role_id={role_id}",
        name=create_user_data.name,
        role_id=role_id,
    )

    return {"status_code": status.HTTP_201_CREATED, "transaction": "Successful"}


async def update_user_by_name(
    db: AsyncSession,
    name: str,
    update_user: CreateUser,
    role_id: int,
):
    logger.info(
        "Attempting to update user: old name='{old_name}', new name='{new_name}', role_id={role_id}",
        old_name=name,
        new_name=update_user.name,
        role_id=role_id,
    )
    if not (await db.execute(select(User).where(User.name == name))).scalar_one_or_none():
        logger.warning(
            "User with name '{name}' not found for update",
            name=name,
        )
        raise HTTPException(404, "User not found")

    if not (await db.execute(select(Role).where(Role.id == role_id))).scalar_one_or_none():
        logger.warning(
            "Role with ID {role_id} not found for updating user '{name}'",
            role_id=role_id,
            name=name,
        )
        raise HTTPException(404, "Role not found")

    await db.execute(
        update(User)
        .where(User.name == name)
        .values(
            name=update_user.name,
            email=update_user.email,
            password_hash=bcrypt_context.hash(update_user.password),
            role_id=role_id,
        )
    )
    await db.commit()

    logger.info(
        "User with name '{old_name}' successfully updated: new name='{new_name}', role_id={role_id}",
        old_name=name,
        new_name=update_user.name,
        role_id=role_id,
    )

    return {"status": "updated"}


async def delete_user(db: AsyncSession, name: str):
    logger.info(
        "Attempting to delete user with name '{name}'",
        name=name,
    )
    result = await db.execute(select(User).where(User.name == name))
    user = result.scalar_one_or_none()

    if not user:
        logger.warning(
            "User with name '{name}' not found for deletion",
            name=name,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with name '{name}' not found",
        )

    await db.execute(delete(User).where(User.name == name))
    await db.commit()

    logger.info(
        "User with name '{name}' successfully deleted",
        name=name,
    )

    return {
        "status_code": status.HTTP_200_OK,
        "transaction": "User deleted successfully",
    }
