from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from db.models import UserRole

# --- Константы кнопок ---
BTN_PROFILE = "👤 Профиль"
BTN_STATS = "📊 Статистика"
BTN_ADD_LEAD = "➕ Добавить лид"
BTN_ADD_PARTNER = "👥 Добавить партнёра"
BTN_DEALS = "📑 Сделки"
BTN_BONUSES = "💰 Бонусы"
BTN_NEWS = "📰 Новости"
BTN_FEEDBACK = "✍ Отзыв"
BTN_ADMIN = "🛠 Админ"
BTN_MODERATOR = "🛡 Модератор"
BTN_INFO = "ℹ Инструкция"

# Админ-панель
BTN_ADMIN_USERS = "👥 Пользователи"
BTN_ADMIN_BONUSES = "💸 Бонусы (админ)"
BTN_ADMIN_BROADCAST = "📣 Рассылка"
BTN_ADMIN_ROLES = "⚙ Роли"
BTN_ADMIN_STATS = "📊 Глоб. статистика"
BTN_BACK = "↩️ В меню"

# Контент-менеджер
BTN_CM_ADD_NEWS = "📝 Создать новость"
BTN_CM_DRAFTS = "🗂 Черновики"
BTN_CM_PUBLISH = "✅ Публиковать"

# Модератор
BTN_MOD_LEADS = "📋 Проверка лидов"
BTN_MOD_REVIEWS = "🔎 Модерация отзывов"


def main_menu(role: UserRole | None = None) -> ReplyKeyboardMarkup:
    """
    Главное меню. Для любых ролей показываем базовые разделы.
    Для админа, контент-менеджера и модератора добавляем спец.кнопки.
    """
    buttons = [
        [KeyboardButton(text=BTN_PROFILE), KeyboardButton(text=BTN_STATS)],
        [KeyboardButton(text=BTN_ADD_LEAD), KeyboardButton(text=BTN_ADD_PARTNER)],
        [KeyboardButton(text=BTN_DEALS), KeyboardButton(text=BTN_BONUSES)],
        [KeyboardButton(text=BTN_NEWS), KeyboardButton(text=BTN_INFO)],
        [KeyboardButton(text=BTN_FEEDBACK)],
    ]

    if role == UserRole.admin:
        buttons.append([KeyboardButton(text=BTN_ADMIN)])
    elif role == UserRole.content:
        buttons.append([KeyboardButton(text=BTN_ADMIN)])  # контент-менеджер работает через админку
    elif role == UserRole.moderator:
        buttons.append([KeyboardButton(text=BTN_MODERATOR)])

    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
        input_field_placeholder="Выберите раздел…"
    )


def admin_menu() -> ReplyKeyboardMarkup:
    """Меню администратора (reply)."""
    buttons = [
        [KeyboardButton(text=BTN_ADMIN_USERS), KeyboardButton(text=BTN_ADMIN_BONUSES)],
        [KeyboardButton(text=BTN_ADMIN_BROADCAST), KeyboardButton(text=BTN_ADMIN_ROLES)],
        [KeyboardButton(text=BTN_ADMIN_STATS), KeyboardButton(text=BTN_INFO)],
        [KeyboardButton(text=BTN_BACK)],
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


def content_manager_menu() -> ReplyKeyboardMarkup:
    """Меню контент-менеджера (работа с новостями)."""
    buttons = [
        [KeyboardButton(text=BTN_CM_ADD_NEWS), KeyboardButton(text=BTN_CM_DRAFTS)],
        [KeyboardButton(text=BTN_CM_PUBLISH), KeyboardButton(text=BTN_INFO)],
        [KeyboardButton(text=BTN_BACK)],
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


def moderator_menu() -> ReplyKeyboardMarkup:
    """Меню модератора (проверка лидов и отзывов)."""
    buttons = [
        [KeyboardButton(text=BTN_MOD_LEADS), KeyboardButton(text=BTN_MOD_REVIEWS)],
        [KeyboardButton(text=BTN_INFO), KeyboardButton(text=BTN_BACK)],
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


# Алиасы
main_menu_kb = main_menu
user_main_kb = main_menu
admin_menu_kb = admin_menu
content_manager_kb = content_manager_menu
moderator_menu_kb = moderator_menu
