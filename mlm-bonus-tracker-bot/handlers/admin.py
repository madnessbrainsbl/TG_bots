from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from db import get_session
from db.models import User, UserRole
from keyboards.inline import role_select_kb, confirm_kb

from sqlalchemy.future import select

router = Router()


# --- Админ-панель ---
@router.message(F.text == "🛠 Админ")
async def admin_panel(message: Message):
    async with get_session() as session:
        result = await session.execute(select(User).where(User.id == message.from_user.id))
        user = result.scalars().first()

    if not user or user.role not in [UserRole.admin, UserRole.moderator]:
        return await message.answer("⛔ У вас нет доступа к админ-панели")

    await message.answer(
        "⚙ Админ-панель:\n"
        "- Управление ролями\n"
        "- Рассылки\n"
        "- Модерация бонусов и контента",
    )


# --- Назначение ролей ---
@router.message(F.text.startswith("role:"))
async def set_role_command(message: Message):
    try:
        user_id = int(message.text.replace("role:", "").strip())
    except ValueError:
        return await message.answer("❌ Укажите корректный ID пользователя")

    await message.answer(
        f"Выберите роль для пользователя {user_id}:",
        reply_markup=role_select_kb(user_id)
    )


@router.callback_query(F.data.startswith("role:set:"))
async def set_role_callback(call: CallbackQuery):
    _, _, user_id, role = call.data.split(":")
    user_id = int(user_id)

    if role not in UserRole.__members__:
        return await call.message.edit_text("❌ Указана неверная роль")

    async with get_session() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalars().first()
        if not user:
            return await call.message.edit_text("❌ Пользователь не найден")

        user.role = UserRole[role]
        await session.commit()

    await call.message.edit_text(f"✅ Пользователю {user_id} назначена роль: {role}")


# --- Рассылка ---
@router.message(F.text.startswith("broadcast:"))
async def broadcast_prepare(message: Message, state: FSMContext):
    text = message.text.replace("broadcast:", "").strip()
    if not text:
        return await message.answer("❌ Укажите текст рассылки")

    await state.update_data(broadcast_text=text)
    await message.answer(
        f"📢 Подтвердите рассылку:\n\n{text}",
        reply_markup=confirm_kb("broadcast", 0)
    )


@router.callback_query(F.data.startswith("broadcast:yes"))
async def broadcast_confirm(call: CallbackQuery, state: FSMContext, bot):
    data = await state.get_data()
    text = data.get("broadcast_text", "")

    async with get_session() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()

    sent, failed = 0, 0
    for u in users:
        try:
            await bot.send_message(u.id, f"📢 {text}")
            sent += 1
        except Exception:
            failed += 1
            continue

    await call.message.edit_text(f"✅ Рассылка завершена.\nОтправлено: {sent}, ошибок: {failed}")
    await state.clear()


@router.callback_query(F.data.startswith("broadcast:no"))
async def broadcast_cancel(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("❌ Рассылка отменена.")
