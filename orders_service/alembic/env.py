import os
import sys
import asyncio
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine
from alembic import context

# -------------------------------------------------
# Пути
# -------------------------------------------------
current_dir = os.path.dirname(__file__)
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

# -------------------------------------------------
# Загрузка .env
# -------------------------------------------------
from dotenv import load_dotenv
load_dotenv(os.path.join(project_root, ".env"))

# -------------------------------------------------
# Импорт моделей
# -------------------------------------------------
from app.db import Base
from app.models.order import Order
from app.models.order_item import OrderItem

# -------------------------------------------------
# Alembic Config
# -------------------------------------------------
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# -------------------------------------------------
# Настройка подключения к БД
# -------------------------------------------------
env_db_host = os.getenv("DB_HOST", "")
env_db_port = os.getenv("DB_PORT", "")

# Определяем, в контейнере мы или локально
# Если DB_HOST=orders_db недоступен, значит Alembic запущен локально
try:
    import socket
    socket.gethostbyname(env_db_host)
    # Если имя resolve'ится — работаем как есть (контейнер)
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        f"postgresql+asyncpg://user:pass@{env_db_host}:{env_db_port}/orders_db"
    )
except socket.gaierror:
    # Если имя не найдено — работаем локально
    DATABASE_URL = "postgresql+asyncpg://user:pass@localhost:5435/orders_db"

# Устанавливаем URL в конфиг Alembic
config.set_main_option("sqlalchemy.url", DATABASE_URL)

# -------------------------------------------------
# OFFLINE режим
# -------------------------------------------------
def run_migrations_offline():
    """Запуск миграций без подключения (генерация SQL)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()

# -------------------------------------------------
# ONLINE режим
# -------------------------------------------------
def do_run_migrations(connection: Connection):
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()

async def run_migrations_online():
    connectable = create_async_engine(DATABASE_URL, poolclass=pool.NullPool)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()

# -------------------------------------------------
# Точка входа
# -------------------------------------------------
if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
