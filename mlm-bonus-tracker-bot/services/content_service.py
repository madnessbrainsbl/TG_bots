
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Content
from db.db import async_session


async def add_news(title: str, text: str):
    """
    Добавить новость в базу.
    """
    async with async_session() as session:  # type: AsyncSession
        news = Content(title=title, text=text)
        session.add(news)
        await session.commit()
        await session.refresh(news)
        return news


async def list_news():
    """
    Получить список всех новостей (новые сверху).
    """
    async with async_session() as session:  # type: AsyncSession
        result = await session.execute(select(Content).order_by(Content.created_at.desc()))
        return result.scalars().all()
