import asyncio
import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine

# --- путь до корня проекта, чтобы импортировать db.models ---
THIS_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(THIS_DIR, os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Импортируем metadata из моделей
from db.models import Base  # noqa: E402

# Alembic Config object
config = context.config

# Logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Целевая метадата для генерации миграций
target_metadata = Base.metadata


def get_url() -> str:
    """Определение URL подключения к БД."""
    # Берем из переменной окружения (например, DB_URL в .env)
    url = os.getenv("DB_URL")
    if url:
        return url
    # fallback — читаем из alembic.ini
    return config.get_main_option("sqlalchemy.url", "sqlite+aiosqlite:///bot.db")


def _is_sqlite(url: str) -> bool:
    return url.startswith("sqlite")


def run_migrations_offline() -> None:
    """Offline режим: генерирует SQL без подключения к базе."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        compare_server_default=True,
        render_as_batch=_is_sqlite(url),
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Online режим: миграции выполняются в реальной базе (async)."""
    connectable = create_async_engine(
        get_url(),
        pool_pre_ping=True,
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(
            lambda sync_conn: context.configure(
                connection=sync_conn,
                target_metadata=target_metadata,
                compare_type=True,
                compare_server_default=True,
                render_as_batch=_is_sqlite(str(sync_conn.engine.url)),
            )
        )
        with context.begin_transaction():
            context.run_migrations()
    await connectable.dispose()


def run_migrations() -> None:
    """Запуск миграций в зависимости от режима."""
    if context.is_offline_mode():
        run_migrations_offline()
    else:
        asyncio.run(run_migrations_online())


run_migrations()
