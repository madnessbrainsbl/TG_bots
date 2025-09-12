from aiogram import Router, types, F
from aiogram.filters import Command
from sqlalchemy import select
from db import get_session
from db.models import News, User, UserRole
from keyboards.inline import confirm_news_kb

router = Router()


# --- Пользователь: просмотр новостей ---
@router.message(F.text == "📰 Новости")
async def show_news(message: types.Message):
    async with get_session() as session:
        result = await session.execute(
            select(News)
            .where(News.is_active == True)
            .order_by(News.created_at.desc())
            .limit(10)
        )
        news_list = result.scalars().all()

    if not news_list:
        await message.answer("📰 Пока новостей нет.")
        return

    text = "📰 <b>Последние новости:</b>\n\n"
    for n in news_list:
        text += f"📌 <b>{n.title}</b>\n{n.content}\n\n"

    await message.answer(text, parse_mode="HTML")


# --- Админ/контент-менеджер: публикация новости ---
@router.message(Command("publish_news"))
async def publish_news(message: types.Message):
    async with get_session() as session:
        user = await session.get(User, message.from_user.id)

    if not user or user.role not in (UserRole.ADMIN, UserRole.CONTENT_MANAGER):
        await message.answer("⛔ У вас нет прав для публикации новостей.")
        return

    await message.answer(
        "✍️ Введите новость в формате:\n\n"
        "NEWS:<заголовок>\n\n<содержимое>"
    )


# --- Админ/контент-менеджер: обработка текста новости ---
@router.message(F.text.startswith("NEWS:"))
async def process_news(message: types.Message):
    """
    Формат ввода: NEWS:<заголовок>\n\n<содержимое>
    """
    try:
        _, raw = message.text.split("NEWS:", 1)
        title, content = raw.strip().split("\n\n", 1)
    except ValueError:
        await message.answer("⚠️ Неверный формат. Используйте:\nNEWS:<заголовок>\n\n<содержимое>")
        return

    async with get_session() as session:
        user = await session.get(User, message.from_user.id)

        if not user or user.role not in (UserRole.ADMIN, UserRole.CONTENT_MANAGER):
            await message.answer("⛔ У вас нет прав для публикации новостей.")
            return

        news = News(
            title=title.strip(),
            content=content.strip(),
            author_id=user.id,
            is_active=True,
        )
        session.add(news)
        await session.commit()

    await message.answer(
        f"✅ Новость сохранена:\n\n📌 <b>{title}</b>\n{content}",
        parse_mode="HTML",
        reply_markup=confirm_news_kb(news.id),
    )


# --- Админ: подтверждение и рассылка ---
@router.callback_query(F.data.startswith("confirm_news"))
async def confirm_news(callback: types.CallbackQuery):
    async with get_session() as session:
        result = await session.execute(select(User.tg_id).where(User.tg_id.isnot(None)))
        users = result.scalars().all()

    # Рассылка всем пользователям
    sent = 0
    for uid in users:
        try:
            await callback.bot.send_message(uid, callback.message.text, parse_mode="HTML")
            sent += 1
        except Exception:
            continue

    await callback.message.edit_text(f"✅ Новость опубликована и разослана {sent} пользователям.")
    await callback.answer("Рассылка завершена ✅", show_alert=True)
