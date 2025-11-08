import os
import sys
import asyncio
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine
from alembic import context


current_dir = os.path.dirname(__file__)
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)


from dotenv import load_dotenv
load_dotenv(os.path.join(project_root, ".env"))


from app.db import Base
from app.models.order import Order
from app.models.order_item import OrderItem


config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


env_db_host = os.getenv("DB_HOST", "")
env_db_port = os.getenv("DB_PORT", "")


try:
    import socket
    socket.gethostbyname(env_db_host)
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        f"postgresql+asyncpg://user:pass@{env_db_host}:{env_db_port}/orders_db"
    )
except socket.gaierror:
    DATABASE_URL = "postgresql+asyncpg://user:pass@localhost:5435/orders_db"


config.set_main_option("sqlalchemy.url", DATABASE_URL)


def run_migrations_offline():
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


def do_run_migrations(connection: Connection):
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()

async def run_migrations_online():
    connectable = create_async_engine(DATABASE_URL, poolclass=pool.NullPool)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
