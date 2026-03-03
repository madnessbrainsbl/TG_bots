from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from keyboards.reply import (
    main_menu,
    main_menu_kb,
    admin_menu_kb,
    content_manager_kb,
    moderator_menu_kb,
)
from keyboards.inline import role_select_inline_kb
from config import Settings
from db.models import UserRole

router = Router(name="roles")
settings = Settings()


# --- Вспомогательные функции ---
def is_admin(tg_id: int) -> bool:
    """Проверка, является ли пользователь админом (по списку в .env)"""
    return tg_id in settings.ADMIN_IDS


# --- Переключение ролей ---
@router.message(Command("role"))
@router.message(F.text == "🔄 Переключить роль")
async def role_switch_entry(message: types.Message, state: FSMContext):
    """Точка входа для переключения роли (только админы)"""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Команда доступна только администраторам.")
        return

    await message.answer(
        "Выберите роль, под которой показывать меню:",
        reply_markup=role_select_inline_kb(),
    )


@router.callback_query(F.data.startswith("role:set:"))
async def cb_set_role(cb: types.CallbackQuery, state: FSMContext):
    """Обработка выбора роли (имперсонация админом)"""
    if not is_admin(cb.from_user.id):
        await cb.answer("Только для админов", show_alert=True)
        return

    _, _, role_str = cb.data.split(":")

    try:
        role = UserRole(role_str)
    except ValueError:
        await cb.answer("❌ Неверная роль", show_alert=True)
        return

    await state.update_data(impersonate_role=role.value)
    await cb.answer(f"Роль переключена на: {role.value}")

    # показать меню в соответствии с выбранной ролью
    if role == UserRole.admin:
        kb = admin_menu_kb()
        title = "👑 Режим администратора"
    elif role == UserRole.content:
        kb = content_manager_kb()
        title = "📰 Режим контент-менеджера"
    elif role == UserRole.moderator:
        kb = moderator_menu_kb()
        title = "🛡 Режим модератора"
    else:
        kb = main_menu_kb()
        title = "👤 Режим партнёра"

    await cb.message.answer(
        f"{title}. Для возврата к своему меню используйте кнопку «🏠 Меню партнёра».",
        reply_markup=kb,
    )


@router.message(F.text == "🏠 Меню партнёра")
async def back_to_user_menu(message: types.Message, state: FSMContext):
    """Возврат к обычному партнёрскому меню"""
    await state.update_data(impersonate_role=UserRole.partner.value)
    await message.answer("Главное меню партнёра:", reply_markup=main_menu_kb())


@router.message(Command("menu"))
async def show_current_menu(message: types.Message, state: FSMContext):
    """Показ текущего меню в зависимости от выбранной роли (имперсонации)"""
    data = await state.get_data()
    role_str = data.get("impersonate_role", UserRole.partner.value)

    try:
        role = UserRole(role_str)
    except ValueError:
        role = UserRole.partner

    await message.answer(
        f"Текущая роль отображения: {role.value}",
        reply_markup=main_menu(role)
    )
