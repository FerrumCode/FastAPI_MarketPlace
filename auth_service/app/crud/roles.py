from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy import select, update, delete
from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.role import Role
from app.schemas.role import CreateRole
from app.db_depends import get_db
from app.dependencies.auth import verify_admin_and_get_user

router = APIRouter(prefix='/role', tags=['Role'])


async def get_roles_from_db(db: Annotated[AsyncSession, Depends(get_db)]):
    try:
        query = select(Role)
        result = await db.execute(query)
        roles = result.scalars().all()  # Для получения объектов Role

        return roles

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при получении пользователей: {str(e)}"
        )


async def create_role_in_db(
    db: Annotated[AsyncSession,
    Depends(get_db)],
    create_role: CreateRole,
):
    try:
        # ПРАВИЛЬНАЯ проверка: ищем роль с таким же именем
        result = await db.execute(
            select(Role).where(Role.name == create_role.name)
        )
        existing_role = result.scalar_one_or_none()

        # ЕСЛИ роль найдена - выдаем ошибку
        if existing_role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Роль с именем '{create_role.name}' уже существует"
            )

        # ЕСЛИ роль НЕ найдена - создаем новую
        new_role = Role(
            name=create_role.name,
            description=create_role.description
        )

        db.add(new_role)
        await db.commit()
        await db.refresh(new_role)

        return {
            'status_code': status.HTTP_201_CREATED,
            'message': 'Роль успешно создана',
            'role': new_role
        }

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при создании роли: {str(e)}"
        )


async def update_role_in_db(
        db: Annotated[AsyncSession, Depends(get_db)],
        role_name: str,
        role_data: CreateRole
):
    try:
        # 1. Проверяем, существует ли роль с таким именем
        result = await db.execute(
            select(Role).where(Role.name == role_name)
        )
        role = result.scalar_one_or_none()

        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Роль с именем '{role_name}' не найдена"
            )

        # 2. Проверяем, не существует ли уже роли с новым именем (если имя меняется)
        if role_data.name != role_name:  # ИСПРАВЛЕНО: role_data вместо update_role
            result = await db.execute(
                select(Role).where(Role.name == role_data.name)  # ИСПРАВЛЕНО
            )
            existing_role = result.scalar_one_or_none()

            if existing_role:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Роль с именем '{role_data.name}' уже существует"  # ИСПРАВЛЕНО
                )

        # 3. Обновляем роль
        await db.execute(
            update(Role)
            .where(Role.name == role_name)
            .values(
                name=role_data.name,  # ИСПРАВЛЕНО: role_data вместо update_role
                description=role_data.description  # ИСПРАВЛЕНО
            )
        )
        await db.commit()

        return {
            'status': 'success',
            'message': 'Роль успешно обновлена',
            'old_name': role_name,
            'new_name': role_data.name,  # ИСПРАВЛЕНО
            'new_description': role_data.description  # ИСПРАВЛЕНО
        }

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при обновлении роли: {str(e)}"
        )


async def delete_user_from_db(
    db: Annotated[AsyncSession, Depends(get_db)],
    name: str,
):
    # Проверяем существование роли
    role_result = await db.execute(select(Role).where(Role.name == name))
    role = role_result.scalar_one_or_none()

    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Роль с именем '{name}' не найден"
        )

    # Удаляем пользователя
    await db.execute(
        delete(Role)
        .where(Role.name == name)
    )
    await db.commit()

    return {
        'status_code': status.HTTP_200_OK,
        'transaction': 'Role deleted successfully'
    }