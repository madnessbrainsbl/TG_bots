# db.py
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker

# Базовый класс для всех моделей
Base = declarative_base()

# URL для подключения к базе (берём из переменной окружения или используем SQLite по умолчанию)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./bot.db")

# Создаём движок
engine = create_async_engine(DATABASE_URL, echo=False, future=True)

# Фабрика сессий
async_session_factory = sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)


# ✅ Получение сессии
def get_session() -> AsyncSession:
    """
    Возвращает асинхронный контекст-менеджер сессии.
    Использование:
        async with get_session() as session:
            ...
    """
    return async_session_factory()


# ✅ Инициализация базы (создание таблиц)
async def init_db():
    """
    Инициализация базы данных.
    Импортируем все модели, чтобы они зарегистрировались в metadata,
    и создаём таблицы, если их нет.
    """
    import db.models  # обязательно импортируем все модели
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
