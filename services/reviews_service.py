from sqlalchemy import select
from db import get_session
from db.models import Review


async def submit_review(user_id: int, text: str) -> Review:
    """
    Добавить новый отзыв от пользователя.
    """
    async with get_session() as session:
        review = Review(user_id=user_id, text=text)
        session.add(review)
        await session.commit()
        await session.refresh(review)
        return review


async def list_pending_reviews() -> list[Review]:
    """
    Получить список отзывов, ожидающих модерации.
    """
    async with get_session() as session:
        result = await session.execute(
            select(Review).where(Review.approved == False)
        )
        return result.scalars().all()


async def approve_review(review_id: int) -> Review:
    """
    Одобрить отзыв по его ID.
    """
    async with get_session() as session:
        result = await session.execute(
            select(Review).where(Review.id == review_id)
        )
        review = result.scalar_one()
        review.approved = True
        await session.commit()
        await session.refresh(review)
        return review


async def reject_review(review_id: int) -> None:
    """
    Отклонить (удалить) отзыв по его ID.
    """
    async with get_session() as session:
        result = await session.execute(
            select(Review).where(Review.id == review_id)
        )
        review = result.scalar_one()
        await session.delete(review)
        await session.commit()
