from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy import select, update, delete
from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.permission import Permission
from app.schemas.permission import CreatePermission
from app.db_depends import get_db
from app.dependencies.auth import verify_admin_and_get_user

router = APIRouter(prefix='/permission', tags=['Permission'])


@router.get('/get_permissions')
async def get_permissions(db: Annotated[AsyncSession, Depends(get_db)],
                          admin_user: dict = Depends(verify_admin_and_get_user)
):
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


@router.post('/create_permission', status_code=status.HTTP_201_CREATED)
async def create_permission(
    db: Annotated[AsyncSession, Depends(get_db)],
    create_permission: CreatePermission,  # Предполагается схема с полями code и description
    admin_user: dict = Depends(verify_admin_and_get_user)
):
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
            'status_code': status.HTTP_201_CREATED,
            'message': 'Разрешение успешно создано',
            'permission': new_permission
        }

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при создании разрешения: {str(e)}"
        )


@router.put('/change_permission/{permission_code}', status_code=status.HTTP_200_OK)
async def change_permission(
    db: Annotated[AsyncSession, Depends(get_db)],
    permission_code: str,
    permission_data: CreatePermission,  # Схема с новыми данными
    admin_user: dict = Depends(verify_admin_and_get_user)
):
    try:
        # 1. Проверяем, существует ли разрешение с таким кодом
        result = await db.execute(
            select(Permission).where(Permission.code == permission_code)
        )
        permission = result.scalar_one_or_none()

        if not permission:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Разрешение с кодом '{permission_code}' не найдено"
            )

        # 2. Проверяем, не существует ли уже разрешения с новым кодом (если код меняется)
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

        # 3. Обновляем разрешение
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
            'status': 'success',
            'message': 'Разрешение успешно обновлено',
            'old_code': permission_code,
            'new_code': permission_data.code,
            'new_description': permission_data.description
        }

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при обновлении разрешения: {str(e)}"
        )


@router.delete('/delete_permission')
async def delete_permission(
    db: Annotated[AsyncSession, Depends(get_db)],
    code: str,  # Удаляем по коду разрешения
    admin_user: dict = Depends(verify_admin_and_get_user)
):
    try:
        # Проверяем существование разрешения
        permission_result = await db.execute(select(Permission).where(Permission.code == code))
        permission = permission_result.scalar_one_or_none()

        if not permission:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Разрешение с кодом '{code}' не найдено"
            )

        # Удаляем разрешение
        await db.execute(
            delete(Permission)
            .where(Permission.code == code)
        )
        await db.commit()

        return {
            'status_code': status.HTTP_200_OK,
            'message': 'Разрешение успешно удалено'
        }

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при удалении разрешения: {str(e)}"
        )