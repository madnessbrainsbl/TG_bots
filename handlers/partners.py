from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.exceptions import TelegramForbiddenError

from db import get_session
from db.models import User, UserRole
from mlm.tree import process_new_partner
from keyboards.reply import main_menu_kb

router = Router()


class PartnerForm(StatesGroup):
    waiting_for_name = State()
    waiting_for_phone = State()


# --- Добавление партнёра --- #
@router.message(F.text == "➕ Добавить партнёра")
async def add_partner_start(message: types.Message, state: FSMContext):
    await state.set_state(PartnerForm.waiting_for_name)
    await message.answer("✍ Введите имя и фамилию нового партнёра.")


@router.message(PartnerForm.waiting_for_name)
async def add_partner_name(message: types.Message, state: FSMContext):
    await state.update_data(full_name=message.text.strip())
    await state.set_state(PartnerForm.waiting_for_phone)
    await message.answer("📱 Теперь введите телефон партнёра.")


@router.message(PartnerForm.waiting_for_phone)
async def add_partner_phone(message: types.Message, state: FSMContext):
    data = await state.get_data()
    full_name = data["full_name"]
    phone = message.text.strip()

    async with get_session() as session:
        # Проверяем, существует ли текущий пользователь в системе
        sponsor = await session.get(User, message.from_user.id)
        if not sponsor:
            await message.answer("⚠️ Вы не зарегистрированы в системе.")
            return

        # Создаём нового партнёра (без tg_id, пока он сам не зайдёт в бот)
        new_partner = User(
            tg_id=None,
            full_name=full_name,
            phone=phone,
            role=UserRole.partner,
            sponsor_id=sponsor.id  # ✅ связь по дереву
        )
        session.add(new_partner)
        await session.commit()  # чтобы был new_partner.id

        # MLM-логика: начисления, обновления статусов
        await process_new_partner(session, sponsor, new_partner)

    await state.clear()
    await message.answer(
        f"✅ Партнёр <b>{full_name}</b> ({phone}) успешно добавлен!",
        reply_markup=main_menu_kb(sponsor.role),
        parse_mode="HTML"
    )

    # Уведомление самому спонсору
    try:
        await message.bot.send_message(
            message.from_user.id,
            f"🎉 Вы добавили нового партнёра: {full_name} ({phone})."
        )
    except TelegramForbiddenError:
        pass

    # Сообщение в общий чат (если используется)
    await message.bot.send_message(
        message.chat.id,
        f"🆕 Новый партнёр в команде: {full_name} ({phone})"
    )
