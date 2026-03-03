from aiogram import Router, F, types
from aiogram.filters import Command
from config import ADMIN_IDS
from utils.file_utils import load_enabled, save_enabled
from keyboards import admin_menu_kb

router = Router()

@router.message(Command("admin"))
async def admin_menu(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("🚫 У вас нет доступа.")
        return

    enabled = load_enabled()
    await message.answer(
        "🔑 Панель администратора:\nНажми на шаблон, чтобы переключить:",
        reply_markup=admin_menu_kb(enabled)
    )

@router.callback_query(F.data.startswith("toggle:"))
async def toggle_template(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("🚫 Нет доступа", show_alert=True)
        return

    template_name = callback.data.split(":", 1)[1]
    enabled = load_enabled()

    if template_name in enabled:
        enabled[template_name] = not enabled[template_name]
        save_enabled(enabled)
        await callback.message.edit_text(
            "🔑 Панель администратора:\nНажми на шаблон, чтобы переключить:",
            reply_markup=admin_menu_kb(enabled)
        )
        await callback.answer(f"Шаблон {template_name} переключен!")
    else:
        await callback.answer("❌ Шаблон не найден", show_alert=True)
