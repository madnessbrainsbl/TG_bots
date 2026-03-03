from sqlalchemy import select
from sqlalchemy.exc import NoResultFound
from db.db import get_session
from db.models import User, Lead, Deal, Bonus
from mlm.tree import distribute_bonus


async def register_user(telegram_id: int, username: str = None, inviter_id: int = None):
    """
    Регистрирует нового пользователя, если его ещё нет в системе.
    """
    async with get_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalars().first()

        if not user:
            user = User(
                telegram_id=telegram_id,
                username=username,
                inviter_id=inviter_id
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)

        return user


async def create_lead(user_id: int, name: str, phone: str, comment: str = None):
    """
    Создаёт нового лида для пользователя (статус: 'новый').
    """
    async with get_session() as session:
        lead = Lead(
            user_id=user_id,
            name=name,
            phone=phone,
            comment=comment,
            status="новый"
        )
        session.add(lead)
        await session.commit()
        await session.refresh(lead)

        return lead


async def update_lead_status(lead_id: int, new_status: str):
    """
    Обновляет статус лида. Если статус = 'сделка', создаём сделку и начисляем бонусы.
    """
    async with get_session() as session:
        result = await session.execute(select(Lead).where(Lead.id == lead_id))
        lead = result.scalars().first()

        if not lead:
            raise ValueError("Лид не найден")

        lead.status = new_status
        await session.commit()
        await session.refresh(lead)

        # Если лид закрыт в сделку → создаём Deal и бонусы
        if new_status.lower() == "сделка":
            deal = Deal(user_id=lead.user_id, lead_id=lead.id, amount=5000)  # сумма сделки фиксированная по ТЗ
            session.add(deal)
            await session.commit()
            await session.refresh(deal)

            # Начисляем бонусы партнёру и вверх по дереву
            await distribute_bonus(session, lead.user_id, deal.amount)

            return {"lead": lead, "deal": deal}

        return {"lead": lead}


async def get_user_leads(user_id: int):
    """
    Возвращает список лидов пользователя.
    """
    async with get_session() as session:
        result = await session.execute(select(Lead).where(Lead.user_id == user_id))
        return result.scalars().all()


async def get_user_deals(user_id: int):
    """
    Возвращает список сделок пользователя.
    """
    async with get_session() as session:
        result = await session.execute(select(Deal).where(Deal.user_id == user_id))
        return result.scalars().all()


async def get_user_bonuses(user_id: int):
    """
    Возвращает бонусы пользователя.
    """
    async with get_session() as session:
        result = await session.execute(select(Bonus).where(Bonus.user_id == user_id))
        return result.scalars().all()
