from aiogram import Router, types, F
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from db import get_session
from db.models import Lead, Deal, Bonus, User, BonusStatus
from services.bonus_service import accrue_bonus

router = Router()


@router.message(Command("deals"))
async def show_deals(message: types.Message):
    """Показать сделки пользователя"""
    tg_id = message.from_user.id

    async with get_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))
        if not user:
            await message.answer("❌ Вы не зарегистрированы.")
            return

        deals = (await session.execute(
            select(Deal).where(Deal.user_id == user.id)
        )).scalars().all()

    if not deals:
        await message.answer("📑 У вас пока нет сделок.")
        return

    text = "📑 Ваши сделки:\n\n"
    for d in deals:
        text += f"ID: {d.id} | Лид: {d.lead_id} | Сумма: {d.amount} ₽\n"
    await message.answer(text)


@router.message(F.text == "📑 Сделки")
async def deals_menu(message: types.Message):
    await show_deals(message)


async def create_deal_from_lead(session: AsyncSession, lead_id: int, amount: int):
    """
    Перевод лида в сделку и начисление бонуса партнёру + аплайну.
    """
    # Получаем лида
    lead = await session.get(Lead, lead_id)
    if not lead:
        return None

    # Создаём сделку
    deal = Deal(
        user_id=lead.user_id,
        lead_id=lead.id,
        amount=amount
    )
    session.add(deal)

    # Обновляем статус лида
    lead.status = "deal"

    # Начисляем бонусы партнёру и аплайну
    await accrue_bonus(session, lead.user_id, amount, deal.id)

    await session.commit()
    return deal


async def confirm_deal(session: AsyncSession, deal_id: int):
    """
    Админ подтверждает сделку (переводит бонусы в Подтверждено).
    """
    deal = await session.get(Deal, deal_id)
    if not deal:
        return None

    # Бонусы, привязанные к этой сделке, переводим в "Подтверждено"
    bonuses = (await session.execute(
        select(Bonus).where(Bonus.deal_id == deal_id)
    )).scalars().all()

    for bonus in bonuses:
        if bonus.status == BonusStatus.PENDING:
            bonus.status = BonusStatus.APPROVED

    await session.commit()
    return deal
