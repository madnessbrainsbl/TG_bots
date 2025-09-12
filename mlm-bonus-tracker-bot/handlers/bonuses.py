from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

from db import get_session
from db.models import Bonus, BonusStatus, User, UserRole
from services import bonus_service
from keyboards.inline import bonus_admin_kb

router = Router()


@router.message(F.text == "💰 Бонусы")
async def list_bonuses(message: Message):
    """Партнёр смотрит свои бонусы"""
    async with get_session() as session:
        bonuses = await bonus_service.list_user_bonuses(session, message.from_user.id)

    if not bonuses:
        return await message.answer("У вас пока нет бонусов.")

    text_lines = []
    for b in bonuses:
        text_lines.append(f"#{b.id}: {b.amount}₽ — {b.status.value}")

    await message.answer("Ваши бонусы:\n" + "\n".join(text_lines))


@router.message(F.text == "📤 Запросить вывод")
async def request_payout(message: Message):
    """Партнёр запрашивает вывод подтверждённых бонусов"""
    async with get_session() as session:
        totals = await bonus_service.totals_by_status(session, message.from_user.id)
        if totals.get(BonusStatus.approved, 0) <= 0:
            return await message.answer("❌ У вас нет бонусов для вывода.")

        # Переводим все подтверждённые бонусы в статус 'withdrawn'
        approved = await session.execute(
            Bonus.__table__.select().where(
                Bonus.user_id == message.from_user.id,
                Bonus.status == BonusStatus.approved,
            )
        )
        bonuses = approved.scalars().all()
        for b in bonuses:
            b.status = BonusStatus.withdrawn
        await session.commit()

    await message.answer("✅ Запрос на вывод оформлен. Ожидайте перечисления.")


@router.message(F.text == "🛠 Админ: бонусы")
async def admin_bonuses(message: Message):
    """Админ видит бонусы на подтверждение"""
    async with get_session() as session:
        pending = await bonus_service.list_pending_bonuses(session)

    if not pending:
        return await message.answer("Нет бонусов на подтверждение.")

    for b in pending:
        await message.answer(
            f"Бонус #{b.id}\n"
            f"Партнёр: {b.user_id}\n"
            f"Сумма: {b.amount}₽\n"
            f"Статус: {b.status.value}",
            reply_markup=bonus_admin_kb(b.id),
        )


@router.callback_query(F.data.startswith("bonus:approve:"))
async def approve_bonus(callback: CallbackQuery):
    """Админ подтверждает бонус"""
    bonus_id = int(callback.data.split(":")[2])
    async with get_session() as session:
        await bonus_service.approve_bonus(session, bonus_id)

    await callback.message.edit_text(f"✅ Бонус #{bonus_id} подтверждён.")
    await callback.answer("Подтверждено")


@router.callback_query(F.data.startswith("bonus:reject:"))
async def reject_bonus(callback: CallbackQuery):
    """Админ отклоняет бонус"""
    bonus_id = int(callback.data.split(":")[2])
    async with get_session() as session:
        await bonus_service.reject_bonus(session, bonus_id)

    await callback.message.edit_text(f"❌ Бонус #{bonus_id} отклонён.")
    await callback.answer("Отклонено")
