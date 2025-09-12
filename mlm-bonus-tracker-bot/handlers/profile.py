from aiogram import Router, F
from aiogram.types import Message

from db import get_session, User, UserRole
from utils.roles import get_user_status  # ✅ для динамического статуса

router = Router()


@router.message(F.text == "👤 Профиль")
async def show_profile(message: Message):
    """
    Отображение профиля пользователя
    """
    async with get_session() as session:
        user = await session.get(User, message.from_user.id)

        if not user:
            await message.answer("⚠️ Вы ещё не зарегистрированы в системе.")
            return

        # Определяем роль пользователя
        role = {
            UserRole.admin: "Администратор 👑",
            UserRole.moderator: "Модератор 🛡️",
            UserRole.partner: "Партнёр 👤",
            UserRole.client: "Клиент 📱",
            UserRole.content: "Контент-менеджер 📝",
        }.get(user.role, "Неизвестно")

        # Определяем статус динамически
        status = get_user_status(user.status_points)

        text = (
            f"👤 <b>Ваш профиль</b>\n\n"
            f"🆔 ID: <code>{user.id}</code>\n"
            f"📛 Имя: {user.full_name or '-'}\n"
            f"💼 Роль: {role}\n"
            f"⭐️ Статус: {status}\n"
            f"📅 Дата регистрации: {user.created_at.strftime('%d.%m.%Y %H:%M')}\n"
        )

        await message.answer(text)


@router.message(F.text.startswith("/set_role"))
async def set_role_command(message: Message):
    """
    Установка роли пользователю (только для админов).
    Пример: /set_role 123456 moderator
    """
    async with get_session() as session:
        user = await session.get(User, message.from_user.id)

        if not user or user.role != UserRole.admin:
            await message.answer("❌ У вас нет прав для смены ролей.")
            return

        try:
            _, user_id, new_role = message.text.split()
            user_id = int(user_id)
        except ValueError:
            await message.answer("❌ Использование: /set_role <user_id> <admin|moderator|partner|client|content>")
            return

        target_user = await session.get(User, user_id)
        if not target_user:
            await message.answer("❌ Пользователь не найден.")
            return

        try:
            target_user.role = UserRole(new_role)
        except ValueError:
            await message.answer("❌ Недопустимая роль. Используйте: admin, moderator, partner, client, content.")
            return

        await session.commit()

        await message.answer(
            f"✅ Роль пользователя {target_user.full_name or target_user.tg_id} "
            f"изменена на {target_user.role.value}."
        )
