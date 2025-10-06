from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy import select, insert
from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession
from passlib.context import CryptContext

from app.models.user import User
from app.models.role import Role
from app.schemas.user import CreateUser
from app.db_depends import get_db
from sqlalchemy import update, delete
from app.dependencies.auth import verify_admin_and_get_user
from app.dependencies.auth import check_blacklist

router = APIRouter(prefix='/user', tags=['User'])
bcrypt_context = CryptContext(schemes=['bcrypt'], deprecated='auto') # Для хеширования паролей


async def get_all_users(db: AsyncSession):
    try:
        targets = select(
            User.role_id,
            User.name
        )
        result = await db.execute(targets)
        users = result.mappings().all()
        return users
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при получении пользователей: {str(e)}"
        )


async def get_user(db: AsyncSession, name: str):
    try:
            target = select(User).where(User.name == name)
            result = await db.execute(target)
            user = result.scalar_one_or_none()

            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Пользователь с именем '{name}' не найден"
                )
            return user

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при поиске пользователя: {str(e)}"
        )


async def create_user_in_db(
    db: Annotated[AsyncSession, Depends(get_db)],
    create_user_data: CreateUser,
    role_id: int,
):
    # Проверяем существование роли
    result = await db.execute(select(Role).where(Role.id == role_id))
    role = result.scalar_one_or_none()

    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Роль с ID {role_id} не найдена"
        )

    # создаём пользователя с этой ролью
    await db.execute(insert(User).values(name=create_user_data.name,
                                         email=create_user_data.email,
                                         password_hash=bcrypt_context.hash(create_user_data.password),
                                         role_id=role_id
                                         ))
    await db.commit()

    return {
        'status_code': status.HTTP_201_CREATED,
        'transaction': 'Successful'
    }


async def update_user_by_name(
    db: Annotated[AsyncSession, Depends(get_db)],
    name: str,
    update_user: CreateUser,
    role_id: int,
):
    # Проверка пользователя
    if not (await db.execute(select(User).where(User.name == name))).scalar_one_or_none():
        raise HTTPException(404, "User not found")

    # Проверка роли
    if not (await db.execute(select(Role).where(Role.id == role_id))).scalar_one_or_none():
        raise HTTPException(404, "Role not found")

    # Обновление
    await db.execute(update(User).where(User.name == name).values(
            name=update_user.name,
            email=update_user.email,
            password_hash=bcrypt_context.hash(update_user.password),
            role_id=role_id
        )
    )
    await db.commit()

    return {'status': 'updated'}



async def delete_user(
    db: Annotated[AsyncSession, Depends(get_db)],
    name: str
):
    # Проверяем существование пользователя
    user_result = await db.execute(select(User).where(User.name == name))
    user = user_result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Пользователь с именем '{name}' не найден"
        )

    # Удаляем пользователя
    await db.execute(
        delete(User)
        .where(User.name == name)
    )
    await db.commit()

    return {
        'status_code': status.HTTP_200_OK,
        'transaction': 'User deleted successfully'
    }