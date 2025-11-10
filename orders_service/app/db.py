import os
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker


DATABASE_URL = os.environ["DATABASE_URL"]

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession,
    autoflush=False,
)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
