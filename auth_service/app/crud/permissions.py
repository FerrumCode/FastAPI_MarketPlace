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
        "Запрос разрешения из БД с параметрами: id={permission_id}, code={code}",
        permission_id=permission_id,
        code=code,
    )

    if (permission_id is None and code is None) or (
        permission_id is not None and code is not None
    ):
        logger.error(
            "Некорректная комбинация параметров в get_permission_from_db: permission_id={permission_id}, code={code}",
            permission_id=permission_id,
            code=code,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Укажите ровно один параметр: либо id, либо code.",
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
                "Разрешение не найдено в БД по {ident}",
                ident=ident
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Разрешение с {ident} не найдено",
            )

        logger.info(
            "Разрешение успешно получено из БД: id={id}, code={code}",
            id=permission.id,
            code=permission.code,
        )
        return permission

    except HTTPException:
        logger.exception(
            "Возникла HTTPException при получении разрешения из БД"
        )
        raise
    except Exception as e:
        logger.exception(
            "Неожиданная ошибка при получении разрешения из БД"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при получении разрешения: {str(e)}",
        )


async def create_permission_in_db(
    db: AsyncSession,
    create_permission: CreatePermission,
):
    logger.info(
        "Попытка создания нового разрешения с code='{code}'",
        code=create_permission.code,
    )

    try:
        result = await db.execute(
            select(Permission).where(Permission.code == create_permission.code)
        )
        existing_permission = result.scalar_one_or_none()

        if existing_permission:
            logger.warning(
                "Попытка создать уже существующее разрешение с code='{code}'",
                code=create_permission.code,
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Разрешение с кодом '{create_permission.code}' уже существует",
            )

        new_permission = Permission(
            code=create_permission.code,
            description=create_permission.description,
        )

        db.add(new_permission)
        await db.commit()
        await db.refresh(new_permission)

        logger.info(
            "Разрешение успешно создано в БД: id={id}, code={code}",
            id=new_permission.id,
            code=new_permission.code,
        )

        return {
            "status_code": status.HTTP_201_CREATED,
            "message": "Разрешение успешно создано",
            "permission": new_permission,
        }

    except HTTPException:
        logger.exception(
            "Возникла HTTPException при создании разрешения в БД"
        )
        await db.rollback()
        raise
    except Exception as e:
        logger.exception("Неожиданная ошибка при создании разрешения в БД")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при создании разрешения: {str(e)}",
        )


async def change_permission_in_db(
    db: AsyncSession,
    permission_code: str,
    permission_data: CreatePermission,
):
    logger.info(
        "Попытка обновления разрешения с code='{code}'. Новый code='{new_code}'",
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
                "Попытка обновить несуществующее разрешение с code='{code}'",
                code=permission_code,
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Разрешение с кодом '{permission_code}' не найдено",
            )

        if permission_data.code != permission_code:
            logger.debug(
                "Проверка конфликта кода при смене code с '{old_code}' на '{new_code}'",
                old_code=permission_code,
                new_code=permission_data.code,
            )
            result = await db.execute(
                select(Permission).where(Permission.code == permission_data.code)
            )
            existing_permission = result.scalar_one_or_none()

            if existing_permission:
                logger.warning(
                    "Попытка сменить код разрешения на уже существующий code='{code}'",
                    code=permission_data.code,
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Разрешение с кодом '{permission_data.code}' уже существует",
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
            "Разрешение успешно обновлено в БД: old_code='{old_code}', new_code='{new_code}'",
            old_code=permission_code,
            new_code=permission_data.code,
        )

        return {
            "status": "success",
            "message": "Разрешение успешно обновлено",
            "old_code": permission_code,
            "new_code": permission_data.code,
            "new_description": permission_data.description,
        }

    except HTTPException:
        logger.exception(
            "Возникла HTTPException при обновлении разрешения в БД"
        )
        await db.rollback()
        raise
    except Exception as e:
        logger.exception("Неожиданная ошибка при обновлении разрешения в БД")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при обновлении разрешения: {str(e)}",
        )


async def delete_permission_in_db(db: AsyncSession, code: str):
    logger.info(
        "Попытка удаления разрешения с code='{code}' из БД",
        code=code,
    )

    try:
        permission_result = await db.execute(
            select(Permission).where(Permission.code == code)
        )
        permission = permission_result.scalar_one_or_none()

        if not permission:
            logger.warning(
                "Попытка удалить несуществующее разрешение с code='{code}'",
                code=code,
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Разрешение с кодом '{code}' не найдено",
            )

        await db.execute(delete(Permission).where(Permission.code == code))
        await db.commit()

        logger.info(
            "Разрешение с code='{code}' успешно удалено из БД",
            code=code,
        )

        return {
            "status_code": status.HTTP_200_OK,
            "message": "Разрешение успешно удалено",
        }

    except HTTPException:
        logger.exception(
            "Возникла HTTPException при удалении разрешения из БД"
        )
        await db.rollback()
        raise
    except Exception as e:
        logger.exception("Неожиданная ошибка при удалении разрешения из БД")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при удалении разрешения: {str(e)}",
        )
