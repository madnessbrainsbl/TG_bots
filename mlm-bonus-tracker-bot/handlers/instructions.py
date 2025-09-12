from aiogram import Router, F, types
from sqlalchemy import select

from db import get_session  # ✅ правильный импорт
from db.models import User
from keyboards.reply import BTN_INFO
from texts.instructions import INSTRUCTIONS

router = Router(name="instructions")


@router.message(F.text == BTN_INFO)
async def send_role_instruction(message: types.Message):
    """
    Отправка инструкции в зависимости от роли пользователя.
    Если роль неизвестна — показываем партнёрскую инструкцию.
    """
    role = "partner"  # роль по умолчанию

    # ✅ исправлено использование get_session
    async with get_session() as session:
        user = await session.scalar(
            select(User).where(User.tg_id == message.from_user.id)
        )

        if user and user.role:
            role = user.role.lower().strip()

    # Поддержка всех ключей из INSTRUCTIONS
    text = INSTRUCTIONS.get(role, INSTRUCTIONS["partner"])

    # Отправляем текст
    await message.answer(text, parse_mode="HTML")
