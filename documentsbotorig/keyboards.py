from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def admin_menu_kb(enabled):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"{'✅' if flag else '❌'} {name}",
                    callback_data=f"toggle:{name}"
                )
            ]
            for name, flag in enabled.items()
        ]
    )

def confirm_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm")]]
    )

def templates_kb(templates):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t['name'], callback_data=f"template:{t['slug']}")]
            for t in templates
        ]
    )

def table_row_kb():
    """Клавиатура для управления добавлением строк таблицы."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="➕ Добавить строку", callback_data="row:add"),
                InlineKeyboardButton(text="✅ Готово", callback_data="row:done"),
            ]
        ]
    )


def select_kb(options):
    """Клавиатура для выбора значения из списка (type=select)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=str(opt), callback_data=f"opt:{i}")]
            for i, opt in enumerate(options)
        ]
    )


def bool_kb():
    """Клавиатура для булевых значений (Да/Нет)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Да", callback_data="bool:1"),
                InlineKeyboardButton(text="Нет", callback_data="bool:0"),
            ]
        ]
    )
