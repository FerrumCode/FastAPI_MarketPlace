import asyncio
import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy import pool
from dotenv import load_dotenv

# ======================
# Пути проекта
# ======================
current_dir = os.path.dirname(__file__)
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

# ======================
# Импорт моделей
# ======================
from app.db import Base
from app.models.product import Product
from app.models.category import Category

# ======================
# Настройка Alembic
# ======================
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# ======================
# Подключение к БД
# ======================
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5434/catalog_db")
print(f"[ALEMBIC] Using DATABASE_URL = {DATABASE_URL}")
config.set_main_option("sqlalchemy.url", DATABASE_URL)


# ======================
# OFFLINE режим
# ======================
def run_migrations_offline() -> None:
    """Запуск миграций в offline-режиме."""
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


# ======================
# ONLINE режим (ASYNC)
# ======================
async def run_migrations_online() -> None:
    """Запуск миграций в online-режиме через asyncpg."""
    connectable: AsyncEngine = create_async_engine(DATABASE_URL, poolclass=pool.NullPool)

    async with connectable.begin() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def do_run_migrations(connection):
    """Выполнение миграций внутри синхронного контекста."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations() -> None:
    """Главная точка входа."""
    if context.is_offline_mode():
        run_migrations_offline()
    else:
        asyncio.run(run_migrations_online())


if __name__ == "__main__":
    run_migrations()
