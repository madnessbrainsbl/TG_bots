import asyncio
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.exceptions import TelegramForbiddenError
from sqlalchemy import select

from keyboards.inline import review_moderation_kb
from keyboards.reply import main_menu_kb
from db import get_session
from db.models import User, Review, UserRole

router = Router()


# FSM для написания отзыва
class ReviewForm(StatesGroup):
    waiting_for_text = State()


# Пользователь нажал "✍ Отзыв"
@router.message(F.text == "✍ Отзыв")
async def start_review(message: types.Message, state: FSMContext):
    await state.set_state(ReviewForm.waiting_for_text)
    await message.answer("✍ Напишите ваш отзыв. Он будет передан на модерацию.")


# Приём текста от пользователя
@router.message(ReviewForm.waiting_for_text)
async def process_review(message: types.Message, state: FSMContext):
    async with get_session() as session:
        # Найдём пользователя по tg_id
        result = await session.execute(select(User).where(User.tg_id == message.from_user.id))
        user = result.scalar_one_or_none()
        if not user:
            await message.answer("⚠ Вы не зарегистрированы как партнёр.")
            return

        new_review = Review(
            user_id=user.id,
            text=message.text,
            approved=False  # всегда сначала на модерацию
        )
        session.add(new_review)
        await session.commit()

    await state.clear()
    await message.answer(
        "✅ Спасибо! Ваш отзыв отправлен на модерацию.",
        reply_markup=main_menu_kb(user.role)
    )


# Команда для админов и модераторов — список отзывов на модерацию
@router.message(Command("reviews"))
async def list_pending_reviews(message: types.Message):
    async with get_session() as session:
        user = await session.get(User, message.from_user.id)
        if not user or user.role not in [UserRole.admin, UserRole.moderator]:
            return await message.answer("⛔ У вас нет доступа.")

        result = await session.execute(
            select(Review).where(Review.approved == False)
        )
        reviews = result.scalars().all()

    if not reviews:
        return await message.answer("📭 Нет отзывов на модерацию.")

    for review in reviews:
        text = f"📝 Отзыв #{review.id}\n\n{review.text}\n\n👤 User ID: {review.user_id}"
        await message.answer(text, reply_markup=review_moderation_kb(review.id))


# Утилита: безопасная отправка сообщения
async def safe_send(bot, user_id: int, text: str):
    try:
        await bot.send_message(user_id, text)
    except TelegramForbiddenError:
        pass
    except Exception:
        pass


# Одобрение отзыва → отправляем всем пользователям
@router.callback_query(F.data.startswith("approve_review:"))
async def approve_review(callback: types.CallbackQuery):
    review_id = int(callback.data.split(":")[1])
    async with get_session() as session:
        review = await session.get(Review, review_id)
        if not review:
            return await callback.answer("⚠ Отзыв не найден", show_alert=True)

        review.approved = True
        await session.commit()

        # Получаем всех пользователей
        result = await session.execute(select(User))
        users = result.scalars().all()

    # Текст рассылки
    text = f"📰 Новый отзыв:\n\n{review.text}"

    # Рассылка пачками, чтобы не упереться в лимиты Telegram
    tasks = [safe_send(callback.bot, u.tg_id, text) for u in users if u.tg_id]
    for i in range(0, len(tasks), 30):
        await asyncio.gather(*tasks[i:i+30])
        await asyncio.sleep(1)

    # Уведомляем модератора/админа
    await callback.answer("Отзыв одобрен ✅")
    await callback.message.delete()


# Отклонение отзыва
@router.callback_query(F.data.startswith("reject_review:"))
async def reject_review(callback: types.CallbackQuery):
    review_id = int(callback.data.split(":")[1])
    async with get_session() as session:
        review = await session.get(Review, review_id)
        if not review:
            return await callback.answer("⚠ Отзыв не найден", show_alert=True)

        review.approved = False
        await session.commit()

    # Уведомляем автора
    try:
        await callback.bot.send_message(
            review.user.tg_id,
            "❌ Ваш отзыв отклонён модератором/администратором."
        )
    except TelegramForbiddenError:
        pass

    await callback.answer("Отзыв отклонён ❌")
    await callback.message.delete()
