# db.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from config import settings
from db.models import Base  # Используем общее Base из моделей

# URL для подключения к базе из настроек (config.Settings)
DATABASE_URL = settings.DB_URL

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
    import db.models  # регистрация моделей в Base.metadata
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
