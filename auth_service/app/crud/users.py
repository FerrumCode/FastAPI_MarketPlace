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
    logger.info("Запрос пользователя из БД по имени '{name}'", name=name)
    try:
        query = select(User).where(User.name == name)
        result = await db.execute(query)
        user = result.scalar_one_or_none()

        if not user:
            logger.warning(
                "Пользователь с именем '{name}' не найден при запросе",
                name=name,
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Пользователь с именем '{name}' не найден",
            )
        logger.info(
            "Пользователь с именем '{name}' успешно получен из БД",
            name=name,
        )
        return user
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            "Необработанная ошибка при поиске пользователя с именем '{name}'",
            name=name,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при поиске пользователя: {str(e)}",
        )


async def create_user_in_db(
    db: AsyncSession,
    create_user_data: CreateUser,
    role_id: int,
):
    logger.info(
        "Попытка создания пользователя '{name}' с ролью role_id={role_id}",
        name=create_user_data.name,
        role_id=role_id,
    )
    result = await db.execute(select(Role).where(Role.id == role_id))
    role = result.scalar_one_or_none()

    if not role:
        logger.warning(
            "Роль с ID {role_id} не найдена при создании пользователя '{name}'",
            role_id=role_id,
            name=create_user_data.name,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Роль с ID {role_id} не найдена",
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
        "Пользователь '{name}' успешно создан с ролью role_id={role_id}",
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
        "Попытка обновления пользователя: старое имя='{old_name}', новое имя='{new_name}', role_id={role_id}",
        old_name=name,
        new_name=update_user.name,
        role_id=role_id,
    )
    if not (await db.execute(select(User).where(User.name == name))).scalar_one_or_none():
        logger.warning(
            "Пользователь с именем '{name}' не найден для обновления",
            name=name,
        )
        raise HTTPException(404, "User not found")

    if not (await db.execute(select(Role).where(Role.id == role_id))).scalar_one_or_none():
        logger.warning(
            "Роль с ID {role_id} не найдена для обновления пользователя '{name}'",
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
        "Пользователь с именем '{old_name}' успешно обновлён: новое имя='{new_name}', role_id={role_id}",
        old_name=name,
        new_name=update_user.name,
        role_id=role_id,
    )

    return {"status": "updated"}


async def delete_user(db: AsyncSession, name: str):
    logger.info(
        "Попытка удаления пользователя с именем '{name}'",
        name=name,
    )
    result = await db.execute(select(User).where(User.name == name))
    user = result.scalar_one_or_none()

    if not user:
        logger.warning(
            "Пользователь с именем '{name}' не найден для удаления",
            name=name,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Пользователь с именем '{name}' не найден",
        )

    await db.execute(delete(User).where(User.name == name))
    await db.commit()

    logger.info(
        "Пользователь с именем '{name}' успешно удалён",
        name=name,
    )

    return {
        "status_code": status.HTTP_200_OK,
        "transaction": "User deleted successfully",
    }
