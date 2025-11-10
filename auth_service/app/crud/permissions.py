from fastapi import HTTPException, status
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.permission import Permission
from app.schemas.permission import CreatePermission


async def get_permissions_from_db(db: AsyncSession):
    try:
        query = select(Permission)
        result = await db.execute(query)
        permissions = result.scalars().all()
        return permissions

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при получении разрешений: {str(e)}"
        )


async def create_permission_in_db(db: AsyncSession, create_permission: CreatePermission):
    try:
        # Проверяем, существует ли разрешение с таким же кодом
        result = await db.execute(
            select(Permission).where(Permission.code == create_permission.code)
        )
        existing_permission = result.scalar_one_or_none()

        if existing_permission:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Разрешение с кодом '{create_permission.code}' уже существует"
            )

        # Создаем новое разрешение
        new_permission = Permission(
            code=create_permission.code,
            description=create_permission.description
        )

        db.add(new_permission)
        await db.commit()
        await db.refresh(new_permission)

        return {
            "status_code": status.HTTP_201_CREATED,
            "message": "Разрешение успешно создано",
            "permission": new_permission
        }

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при создании разрешения: {str(e)}"
        )


async def change_permission_in_db(
    db: AsyncSession,
    permission_code: str,
    permission_data: CreatePermission
):
    try:
        # Проверяем, существует ли разрешение
        result = await db.execute(
            select(Permission).where(Permission.code == permission_code)
        )
        permission = result.scalar_one_or_none()

        if not permission:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Разрешение с кодом '{permission_code}' не найдено"
            )

        # Проверяем, не существует ли уже разрешения с новым кодом
        if permission_data.code != permission_code:
            result = await db.execute(
                select(Permission).where(Permission.code == permission_data.code)
            )
            existing_permission = result.scalar_one_or_none()

            if existing_permission:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Разрешение с кодом '{permission_data.code}' уже существует"
                )

        # Обновляем разрешение
        await db.execute(
            update(Permission)
            .where(Permission.code == permission_code)
            .values(
                code=permission_data.code,
                description=permission_data.description
            )
        )
        await db.commit()

        return {
            "status": "success",
            "message": "Разрешение успешно обновлено",
            "old_code": permission_code,
            "new_code": permission_data.code,
            "new_description": permission_data.description
        }

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при обновлении разрешения: {str(e)}"
        )


async def delete_permission_in_db(db: AsyncSession, code: str):
    try:
        permission_result = await db.execute(select(Permission).where(Permission.code == code))
        permission = permission_result.scalar_one_or_none()

        if not permission:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Разрешение с кодом '{code}' не найдено"
            )

        await db.execute(delete(Permission).where(Permission.code == code))
        await db.commit()

        return {
            "status_code": status.HTTP_200_OK,
            "message": "Разрешение успешно удалено"
        }

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при удалении разрешения: {str(e)}"
        )