from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

from db import get_session, Payout
from services import bonus_service
from db.models import BonusStatus

router = Router()

# ======================= Пользователь =======================

@router.message(Command("payouts"))
async def request_payout(message: types.Message):
    """Показать пользователю сумму доступных бонусов и предложить вывести"""
    user_id = message.from_user.id

    async with get_session() as session:
        totals = await bonus_service.totals_by_status(session, user_id)
        available = totals.get(BonusStatus.APPROVED, 0)

        if available <= 0:
            await message.answer("❌ У вас нет подтверждённых бонусов для вывода.")
            return

        await message.answer(
            f"💰 Доступно к выводу: <b>{available} ₽</b>\n\n"
            f"Введите сумму, которую хотите вывести:"
        )


@router.message(F.text.regexp(r"^\d+$"))
async def process_payout_amount(message: types.Message):
    """Обработка введенной пользователем суммы для вывода"""
    user_id = message.from_user.id
    amount = int(message.text)

    async with get_session() as session:
        totals = await bonus_service.totals_by_status(session, user_id)
        available = totals.get(BonusStatus.APPROVED, 0)

        if amount <= 0 or amount > available:
            await message.answer("❌ Недостаточно средств или некорректная сумма.")
            return

        # Создаем заявку на вывод
        payout = Payout(user_id=user_id, amount=amount, status="pending")
        session.add(payout)

        # Переводим бонусы в статус "withdrawn"
        await bonus_service.withdraw_bonus(session, user_id, amount)

        await session.commit()

        await message.answer("✅ Заявка на вывод оформлена. Ожидайте подтверждения администратора.")


# ======================= Админ =======================

@router.message(Command("admin_payouts"))
async def list_pending_payouts(message: types.Message):
    """Админ видит все заявки на вывод"""
    async with get_session() as session:
        result = await session.execute(Payout.__table__.select().where(Payout.status == "pending"))
        payouts = result.fetchall()

    if not payouts:
        await message.answer("📭 Нет заявок на вывод.")
        return

    for p in payouts:
        kb = InlineKeyboardBuilder()
        kb.button(text="✅ Подтвердить", callback_data=f"approve_payout:{p.id}")
        kb.button(text="❌ Отклонить", callback_data=f"reject_payout:{p.id}")
        kb.adjust(2)

        await message.answer(
            f"💸 Заявка #{p.id}\n"
            f"👤 Пользователь: {p.user_id}\n"
            f"Сумма: {p.amount} ₽",
            reply_markup=kb.as_markup()
        )


@router.callback_query(F.data.startswith("approve_payout"))
async def approve_payout(callback: types.CallbackQuery):
    """Подтверждение заявки админом"""
    payout_id = int(callback.data.split(":")[1])

    async with get_session() as session:
        payout = await session.get(Payout, payout_id)
        if not payout:
            await callback.answer("Заявка не найдена", show_alert=True)
            return

        payout.status = "approved"
        await session.commit()

    await callback.message.edit_text("✅ Заявка одобрена. Деньги будут перечислены пользователю.")
    await callback.answer("Пользователь уведомлен")

    await callback.bot.send_message(
        payout.user_id,
        "🎉 Ваша заявка на вывод одобрена!\n\n"
        "Деньги будут перечислены в ближайшее время."
    )


@router.callback_query(F.data.startswith("reject_payout"))
async def reject_payout(callback: types.CallbackQuery):
    """Отклонение заявки админом"""
    payout_id = int(callback.data.split(":")[1])

    async with get_session() as session:
        payout = await session.get(Payout, payout_id)
        if not payout:
            await callback.answer("Заявка не найдена", show_alert=True)
            return

        # Возвращаем бонусы пользователю
        await bonus_service.restore_bonus(session, payout.user_id, payout.amount)
        payout.status = "rejected"
        await session.commit()

    await callback.message.edit_text("❌ Заявка отклонена. Бонусы возвращены пользователю.")
    await callback.answer("Пользователь уведомлен")

    await callback.bot.send_message(
        payout.user_id,
        "❌ Ваша заявка на вывод была отклонена.\n\n"
        "Бонусы возвращены на баланс."
    )
