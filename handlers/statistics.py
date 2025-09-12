from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession
import matplotlib.pyplot as plt
import io
from datetime import datetime, timedelta

from db import get_session
from db.models import User, Deal, Bonus, Payout, BonusStatus, DealStatus, PayoutStatus
from mlm.tree import get_structure_stats, get_downline_by_levels
from utils.roles import get_user_status  # ✅ статус динамически

router = Router()


# --- Главное меню статистики --- #
@router.message(Command("statistics"))
@router.message(F.text == "📊 Статистика")
async def statistics_menu(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Личная статистика", callback_data="stats_personal")],
        [InlineKeyboardButton(text="🌳 Сеть по уровням", callback_data="stats_levels")],
        [InlineKeyboardButton(text="📈 Рост сети", callback_data="stats_growth")],
        [InlineKeyboardButton(text="💼 KPI (сделки и выплаты)", callback_data="stats_kpi")]
    ])
    await message.answer("📊 Выберите раздел статистики:", reply_markup=kb)


# --- Личная статистика --- #
@router.callback_query(F.data == "stats_personal")
async def statistics_handler(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    async with get_session() as session:  # type: AsyncSession
        user = await session.get(User, user_id)
        if not user:
            await callback.message.answer("⚠️ Вы ещё не зарегистрированы как партнёр.")
            return

        personal_sales = await get_personal_sales(session, user.id)
        invited_count = await get_invited_count(session, user.id)

        stats = await get_structure_stats(session, user.id)
        structure_count = stats["total_partners"]
        depth = stats["levels"]

        potential, confirmed, withdrawn = await get_bonus_stats(session, user.id)
        status_name = get_user_status(user.status_points)

        text = (
            f"👤 <b>Ваша статистика</b>\n\n"
            f"📈 Личные продажи: <b>{personal_sales} ₽</b>\n"
            f"👥 Приглашено лично: <b>{invited_count}</b>\n"
            f"🌳 Структура: <b>{structure_count}</b> партнёров (глубина {depth})\n\n"
            f"💰 Бонусы:\n"
            f" ├ Потенциал: <b>{potential} ₽</b>\n"
            f" ├ Подтверждено: <b>{confirmed} ₽</b>\n"
            f" └ Выведено: <b>{withdrawn} ₽</b>\n\n"
            f"🎖 Текущий статус: <b>{status_name}</b>"
        )
        await callback.message.answer(text)


# --- Структура по уровням --- #
@router.callback_query(F.data == "stats_levels")
async def statistics_levels(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    async with get_session() as session:
        levels = await get_downline_by_levels(session, user_id, max_depth=10)
        if not levels:
            await callback.message.answer("❌ У вас пока нет партнёров в структуре.")
            return

        text = "🌳 <b>Сеть по уровням</b>\n\n"
        for level, users in levels.items():
            text += f"Уровень {level}: <b>{len(users)}</b> партнёров\n"

        await callback.message.answer(text)


# --- Рост сети по месяцам (график) --- #
@router.callback_query(F.data == "stats_growth")
async def statistics_growth(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    async with get_session() as session:
        today = datetime.today().date()
        start_date = today - timedelta(days=365)

        levels = await get_downline_by_levels(session, user_id, max_depth=10)
        partner_ids = [u.id for users in levels.values() for u in users]

        if not partner_ids:
            await callback.message.answer("❌ У вас пока нет роста сети.")
            return

        result = await session.execute(
            User.__table__.select()
            .with_only_columns(User.created_at)
            .where(User.id.in_(partner_ids), User.created_at >= start_date)
        )
        dates = result.scalars().all()

        monthly = {}
        for d in dates:
            key = d.strftime("%Y-%m")
            monthly[key] = monthly.get(key, 0) + 1

        if not monthly:
            await callback.message.answer("❌ Нет данных для построения графика.")
            return

        plt.figure(figsize=(6, 4))
        months = sorted(monthly.keys())
        values = [monthly[m] for m in months]
        plt.plot(months, values, marker="o")
        plt.xticks(rotation=45, ha="right")
        plt.title("Рост сети по месяцам")
        plt.xlabel("Месяц")
        plt.ylabel("Новые партнёры")
        plt.tight_layout()

        buf = io.BytesIO()
        plt.savefig(buf, format="png")
        buf.seek(0)
        plt.close()

        await callback.message.answer_photo(
            types.input_file.BufferedInputFile(buf.read(), filename="growth.png")
        )


# --- KPI по сделкам и выплатам --- #
@router.callback_query(F.data == "stats_kpi")
async def statistics_kpi(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    async with get_session() as session:
        today = datetime.today().date()
        start_date = today.replace(day=1)  # начало текущего месяца

        # Сделки
        result = await session.execute(
            Deal.__table__.select()
            .with_only_columns(Deal.amount)
            .where(Deal.user_id == user_id, Deal.created_at >= start_date, Deal.status == DealStatus.confirmed)
        )
        deals = result.scalars().all()
        deals_count = len(deals)
        deals_sum = sum(deals) if deals else 0

        # Выплаты
        result = await session.execute(
            Payout.__table__.select()
            .with_only_columns(Payout.amount)
            .where(Payout.user_id == user_id, Payout.created_at >= start_date, Payout.status == PayoutStatus.confirmed)
        )
        payouts = result.scalars().all()
        payouts_count = len(payouts)
        payouts_sum = sum(payouts) if payouts else 0

        avg_check = int(deals_sum / deals_count) if deals_count else 0

        text = (
            f"💼 <b>KPI за {today.strftime('%B %Y')}</b>\n\n"
            f"📈 Сделки: {deals_count} на сумму <b>{deals_sum} ₽</b>\n"
            f"💳 Средний чек: <b>{avg_check} ₽</b>\n\n"
            f"💰 Выплаты: {payouts_count} на сумму <b>{payouts_sum} ₽</b>"
        )
        await callback.message.answer(text)


# --- Вспомогательные функции --- #
async def get_personal_sales(session: AsyncSession, user_id: int) -> int:
    result = await session.execute(
        Deal.__table__.select()
        .with_only_columns(Deal.amount)
        .where(Deal.user_id == user_id, Deal.status == DealStatus.confirmed)
    )
    amounts = result.scalars().all()
    return sum(amounts) if amounts else 0


async def get_invited_count(session: AsyncSession, user_id: int) -> int:
    result = await session.execute(
        User.__table__.select()
        .with_only_columns(User.id)
        .where(User.sponsor_id == user_id)  # ✅ заменено invited_by → sponsor_id
    )
    return len(result.scalars().all())


async def get_bonus_stats(session: AsyncSession, user_id: int) -> tuple[int, int, int]:
    result = await session.execute(
        Bonus.__table__.select().where(Bonus.user_id == user_id)
    )
    bonuses = result.fetchall()
    potential = sum(b.amount for b in bonuses if b.status == BonusStatus.potential)
    confirmed = sum(b.amount for b in bonuses if b.status == BonusStatus.confirmed)
    withdrawn = sum(b.amount for b in bonuses if b.status == BonusStatus.withdrawn)
    return potential, confirmed, withdrawn
