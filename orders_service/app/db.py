import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    # 🔥 fallback для локальных Alembic миграций
    "postgresql+asyncpg://user:pass@localhost:5435/orders_db"
)

# создаём асинхронный движок
engine = create_async_engine(DATABASE_URL, echo=True, future=True)

# создаём фабрику сессий
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False
)

Base = declarative_base()
