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

# token: str = Depends(check_blacklist) вешаем в каждый эндпоинт для блеклистинга
@router.get('/get_users')
async def get_users(db: Annotated[AsyncSession, Depends(get_db)],
                    admin_user: dict = Depends(verify_admin_and_get_user),
                    token: str = Depends(check_blacklist)
                    ):
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


@router.get('/get_user_info/{name}')
async def get_user_info(db: Annotated[AsyncSession, Depends(get_db)], name: str,
                        admin_user: dict = Depends(verify_admin_and_get_user)
                        ):
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


@router.post('/create_user', status_code=status.HTTP_201_CREATED)
async def create_user(db: Annotated[AsyncSession, Depends(get_db)], create_user: CreateUser,
                      role_id: int,
                      admin_user: dict = Depends(verify_admin_and_get_user)
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
    await db.execute(insert(User).values(name=create_user.name,
                                         email=create_user.email,
                                         password_hash=bcrypt_context.hash(create_user.password),
                                         role_id=role_id
                                         ))
    await db.commit()

    return {
        'status_code': status.HTTP_201_CREATED,
        'transaction': 'Successful'
    }


@router.put('/update_user_by_name/{name}', status_code=200)
async def update_user_by_name(
    db: Annotated[AsyncSession, Depends(get_db)],
    name: str,
    update_user: CreateUser,
    role_id: int,
    admin_user: dict = Depends(verify_admin_and_get_user)
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


@router.delete('/delete_user/{name}')
async def delete_user(
    db: Annotated[AsyncSession, Depends(get_db)],
    name: str,
    admin_user: dict = Depends(verify_admin_and_get_user)
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