# app/db.py

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
# УДАЛЕНО: from sqlalchemy.orm import declarative_base  (Base теперь централизованно в app.models.base)
#from app.core.config import get_settings
from app.models.base import Base  # ИЗМЕНЕНО: импортируем общий Base из models/base.py
from env import DATABASE_URL

#settings = get_settings()

engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # можешь True для отладки
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,  # критично, чтобы объект order не стал "detached"
    class_=AsyncSession,
    autoflush=False,
    # autocommit в SQLAlchemy 2.x больше не используется и вызовет TypeError
    # УДАЛЕНО: autocommit=False
)


async def get_db():
    """
    Dependency для FastAPI роутов.
    usage:
        async def handler(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        yield session
