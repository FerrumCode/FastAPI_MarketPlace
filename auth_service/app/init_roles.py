from sqlalchemy import select
from app.models import Role
from app.db import AsyncSessionLocal

async def create_default_roles():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Role).where(Role.name == "user"))
        role = result.scalar_one_or_none()
        if not role:
            new_role = Role(name="user", description="Обычный пользователь")
            session.add(new_role)
            await session.commit()