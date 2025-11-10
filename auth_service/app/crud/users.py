from fastapi import HTTPException, status
from sqlalchemy import select, insert, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from passlib.context import CryptContext

from app.models.user import User
from app.models.role import Role
from app.schemas.user import CreateUser



bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")



async def get_user_from_db(db: AsyncSession, name: str):
    try:
        query = select(User).where(User.name == name)
        result = await db.execute(query)
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Пользователь с именем '{name}' не найден",
            )
        return user
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при поиске пользователя: {str(e)}",
        )


async def create_user_in_db(
    db: AsyncSession,
    create_user_data: CreateUser,
    role_id: int,
):
    result = await db.execute(select(Role).where(Role.id == role_id))
    role = result.scalar_one_or_none()

    if not role:
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

    return {"status_code": status.HTTP_201_CREATED, "transaction": "Successful"}


async def update_user_by_name(
    db: AsyncSession,
    name: str,
    update_user: CreateUser,
    role_id: int,
):
    if not (await db.execute(select(User).where(User.name == name))).scalar_one_or_none():
        raise HTTPException(404, "User not found")

    if not (await db.execute(select(Role).where(Role.id == role_id))).scalar_one_or_none():
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

    return {"status": "updated"}


async def delete_user(db: AsyncSession, name: str):
    result = await db.execute(select(User).where(User.name == name))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Пользователь с именем '{name}' не найден",
        )

    await db.execute(delete(User).where(User.name == name))
    await db.commit()

    return {
        "status_code": status.HTTP_200_OK,
        "transaction": "User deleted successfully",
    }