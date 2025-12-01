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
        "Запрос ролей из БД: role_id={role_id}, role_name={role_name}",
        role_id=role_id,
        role_name=role_name,
    )
    try:
        if role_id is not None and role_name is not None:
            logger.warning(
                "Указаны оба параметра role_id и role_name при запросе ролей: "
                "role_id={role_id}, role_name={role_name}",
                role_id=role_id,
                role_name=role_name,
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Укажите только один параметр поиска: либо id, либо name.",
            )

        if role_id is not None:
            result = await db.execute(select(Role).where(Role.id == role_id))
            role = result.scalar_one_or_none()
            if not role:
                logger.warning(
                    "Роль с id '{role_id}' не найдена при запросе.",
                    role_id=role_id,
                )
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Роль с id '{role_id}' не найдена",
                )
            logger.info("Роль с id '{role_id}' успешно получена.", role_id=role_id)
            return role

        if role_name is not None:
            result = await db.execute(select(Role).where(Role.name == role_name))
            role = result.scalar_one_or_none()
            if not role:
                logger.warning(
                    "Роль с именем '{role_name}' не найдена при запросе.",
                    role_name=role_name,
                )
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Роль с именем '{role_name}' не найдена",
                )
            logger.info(
                "Роль с именем '{role_name}' успешно получена.",
                role_name=role_name,
            )
            return role

        query = select(Role)
        result = await db.execute(query)
        roles = result.scalars().all()
        logger.info("Получен список ролей. Количество: {count}", count=len(roles))
        return roles

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Необработанная ошибка при получении ролей из БД")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при получении ролей: {str(e)}",
        )


async def create_role_in_db(db: AsyncSession, create_role: CreateRole):
    logger.info(
        "Попытка создания роли с именем '{name}'",
        name=create_role.name,
    )
    try:
        result = await db.execute(select(Role).where(Role.name == create_role.name))
        existing_role = result.scalar_one_or_none()

        if existing_role:
            logger.warning(
                "Попытка создать роль с уже существующим именем '{name}'",
                name=create_role.name,
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Роль с именем '{create_role.name}' уже существует"
            )

        new_role = Role(
            name=create_role.name,
            description=create_role.description
        )

        db.add(new_role)
        await db.commit()
        await db.refresh(new_role)

        logger.info(
            "Роль успешно создана. id={id}, name='{name}'",
            id=new_role.id,
            name=new_role.name,
        )

        return {
            "status_code": status.HTTP_201_CREATED,
            "message": "Роль успешно создана",
            "role": new_role
        }

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.exception(
            "Необработанная ошибка при создании роли с именем '{name}'",
            name=create_role.name,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при создании роли: {str(e)}"
        )


async def update_role_in_db(
    db: AsyncSession,
    role_name: str,
    role_data: CreateRole
):
    logger.info(
        "Попытка обновления роли: старое имя='{old_name}', новое имя='{new_name}'",
        old_name=role_name,
        new_name=role_data.name,
    )
    try:
        result = await db.execute(select(Role).where(Role.name == role_name))
        role = result.scalar_one_or_none()

        if not role:
            logger.warning(
                "Роль с именем '{role_name}' не найдена для обновления",
                role_name=role_name,
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Роль с именем '{role_name}' не найдена"
            )

        if role_data.name != role_name:
            result = await db.execute(select(Role).where(Role.name == role_data.name))
            existing_role = result.scalar_one_or_none()
            if existing_role:
                logger.warning(
                    "Попытка переименовать роль '{old_name}' в уже существующее имя '{new_name}'",
                    old_name=role_name,
                    new_name=role_data.name,
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Роль с именем '{role_data.name}' уже существует"
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
            "Роль успешно обновлена: старое имя='{old_name}', новое имя='{new_name}'",
            old_name=role_name,
            new_name=role_data.name,
        )

        return {
            "status": "success",
            "message": "Роль успешно обновлена",
            "old_name": role_name,
            "new_name": role_data.name,
            "new_description": role_data.description,
        }

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.exception(
            "Необработанная ошибка при обновлении роли '{role_name}'",
            role_name=role_name,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при обновлении роли: {str(e)}"
        )


async def delete_role_from_db(db: AsyncSession, name: str):
    logger.info(
        "Попытка удаления роли с именем '{name}'",
        name=name,
    )
    result = await db.execute(select(Role).where(Role.name == name))
    role = result.scalar_one_or_none()

    if not role:
        logger.warning(
            "Роль с именем '{name}' не найдена для удаления",
            name=name,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Роль с именем '{name}' не найдена"
        )

    await db.execute(delete(Role).where(Role.name == name))
    await db.commit()

    logger.info(
        "Роль с именем '{name}' успешно удалена",
        name=name,
    )

    return {
        "status_code": status.HTTP_200_OK,
        "transaction": "Role deleted successfully"
    }
