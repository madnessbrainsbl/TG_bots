from aiogram import Router, F
from aiogram.types import Message
from sqlalchemy import select

from db import get_session
from db.models import Lead, User, Deal, DealStatus
from services.bonus_service import accrue_bonus

router = Router()


@router.message(F.text == "➕ Добавить лид")
async def add_lead(message: Message):
    """
    Старт добавления лида: просим ввести данные в формате Имя, Телефон
    """
    await message.answer(
        "✍ Введите данные лида в формате:\n"
        "Имя, Телефон\n\n"
        "Пример: Иван Иванов, +79990000000\n\n"
        "После этого отправьте команду:\n"
        "<code>lead:Иван Иванов,+79990000000</code>"
    )


@router.message(F.text.startswith("lead:"))
async def process_lead(message: Message):
    """
    Обработка ввода лида от партнёра.
    Формат: lead:Имя,Телефон
    """
    parts = message.text.replace("lead:", "").split(",")
    if len(parts) < 2:
        return await message.answer("❌ Неверный формат. Введите: Имя, Телефон")

    name, phone = parts[0].strip(), parts[1].strip()

    async with get_session() as session:
        # проверим, есть ли партнёр в системе
        result = await session.execute(select(User).where(User.tg_id == message.from_user.id))
        user = result.scalar_one_or_none()
        if not user:
            return await message.answer("❌ Вы не зарегистрированы как партнёр.")

        new_lead = Lead(
            name=name,
            phone=phone,
            status="new",
            user_id=user.id  # ✅ правильно: связь через user_id
        )
        session.add(new_lead)
        await session.commit()

    await message.answer(f"✅ Лид {name} добавлен и ожидает обработки.")


@router.message(F.text.startswith("lead_status:"))
async def update_lead_status(message: Message):
    """
    Обновление статуса лида.
    Формат: lead_status:<id>,<новый_статус>
    """
    data = message.text.replace("lead_status:", "").split(",")
    if len(data) < 2:
        return await message.answer("❌ Укажите ID лида и новый статус")

    lead_id, new_status = int(data[0]), data[1].strip()

    async with get_session() as session:
        result = await session.execute(select(Lead).where(Lead.id == lead_id))
        lead = result.scalar_one_or_none()

        if not lead:
            return await message.answer("❌ Лид не найден")

        lead.status = new_status

        # если лид стал сделкой → создаём Deal и начисляем бонус партнёру
        if new_status.lower() == "deal":
            deal = Deal(
                user_id=lead.user_id,
                amount=5000,  # TODO: сумму можно будет сделать динамической
                status=DealStatus.confirmed
            )
            session.add(deal)
            await accrue_bonus(session, lead.user_id, deal.amount)

        await session.commit()

    await message.answer(f"✅ Лид #{lead_id} обновлён: {new_status}")
