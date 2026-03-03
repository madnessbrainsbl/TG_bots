from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# --- Лиды ---
LEAD_STATUSES = ["новый", "консультация", "сделка", "брак"]


def lead_status_kb(lead_id: int) -> InlineKeyboardMarkup:
    """
    Кнопки смены статуса лида.
    Колбэки в формате: lead_status:{lead_id}:{status}
    """
    rows = [
        [InlineKeyboardButton(text=s.capitalize(), callback_data=f"lead_status:{lead_id}:{s}")]
        for s in LEAD_STATUSES
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


# --- Бонусы (модерация) ---
def bonus_moderation_kb(bonus_id: int) -> InlineKeyboardMarkup:
    """
    Кнопки подтверждения/отклонения бонуса.
    Колбэки: bonus:approve:{id} / bonus:reject:{id}
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"bonus:approve:{bonus_id}")],
        [InlineKeyboardButton(text="⛔ Отклонить", callback_data=f"bonus:reject:{bonus_id}")],
    ])


# --- Отзывы (модерация) ---
def review_moderation_kb(review_id: int) -> InlineKeyboardMarkup:
    """
    Кнопки для модерации отзыва.
    Колбэки: review:approve:{id} / review:reject:{id}
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Одобрить", callback_data=f"review:approve:{review_id}")],
        [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"review:reject:{review_id}")],
    ])


# --- Роли ---
def role_select_kb(user_id: int) -> InlineKeyboardMarkup:
    """
    Выбор роли пользователю.
    Колбэки: role:set:{user_id}:{role}
    """
    roles = [
        ("👑 Admin", "admin"),
        ("📰 Content", "content"),
        ("🛡️ Moderator", "moderator"),
        ("🤝 Partner", "partner"),
    ]
    rows = [
        [InlineKeyboardButton(text=title, callback_data=f"role:set:{user_id}:{code}")]
        for title, code in roles
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


# --- Алиас для совместимости с handlers/roles.py ---
def role_select_inline_kb(user_id: int | None = None) -> InlineKeyboardMarkup:
    """
    Старое название для функции выбора роли.
    Если user_id не нужен (например, в админке для self-switch),
    используем user_id=0.
    """
    return role_select_kb(user_id or 0)


# --- Подтверждение действий (например, рассылка) ---
def confirm_kb(prefix: str, entity_id: int) -> InlineKeyboardMarkup:
    """
    Универсальное подтверждение действия.
    Колбэки: {prefix}:yes:{id} / {prefix}:no:{id}
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да", callback_data=f"{prefix}:yes:{entity_id}"),
            InlineKeyboardButton(text="❌ Нет", callback_data=f"{prefix}:no:{entity_id}"),
        ]
    ])


# --- Алиасы для совместимости ---
def bonus_admin_kb(bonus_id: int) -> InlineKeyboardMarkup:
    """Старый алиас для бонусов (handlers/bonuses.py)"""
    return bonus_moderation_kb(bonus_id)


# --- Новости (подтверждение публикации) ---
def confirm_news_kb(news_id: int) -> InlineKeyboardMarkup:
    """
    Кнопки для подтверждения/отклонения новости.
    Колбэки: confirm_news:{id} / reject_news:{id}
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить и разослать", callback_data=f"confirm_news:{news_id}")],
        [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_news:{news_id}")],
    ])
