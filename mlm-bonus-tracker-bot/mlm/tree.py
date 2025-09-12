# Bot/mlm/tree.py

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from aiogram import Router, types, F
from aiogram.filters import Command
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from db import get_session
from db.models import User, Bonus, BonusStatus
from mlm.status import get_user_status  # ✅ централизованная логика статусов

router = Router()

# ---------------------- Фоллбэки ----------------------

DEFAULT_LEVELS = {
    1: 1000, 2: 900, 3: 800, 4: 700, 5: 600,
    6: 500, 7: 400, 8: 300, 9: 200, 10: 100,
}


def _get_line_payouts() -> Dict[int, int]:
    """
    settings.MLM_LEVELS приходит из .env как словарь со строковыми ключами.
    Приводим ключи к int.
    """
    if not settings.MLM_LEVELS:
        return DEFAULT_LEVELS
    result: Dict[int, int] = {}
    for k, v in settings.MLM_LEVELS.items():
        try:
            result[int(k)] = int(v)
        except Exception:
            continue
    return result if result else DEFAULT_LEVELS


# ---------------------- Бизнес-логика ----------------------

async def update_partner_status(user: User, session: AsyncSession):
    """
    Пересчёт статуса партнёра на основе его status_points.
    """
    points = getattr(user, "status_points", 0) or 0
    user.status = get_user_status(points)
    await session.commit()


async def _get_user(session: AsyncSession, user_id: int) -> Optional[User]:
    result = await session.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def accrue_bonus(payer_id: int, session: AsyncSession):
    """
    Начисление потенциальных бонусов аплайнам при событии в нижней ветке.
    Идём вверх по цепочке invited_by, используя выплаты из MLM_LEVELS.
    """
    line_payouts = _get_line_payouts()
    max_level = max(line_payouts.keys()) if line_payouts else 0

    current_user_id = payer_id
    level = 1

    while level <= max_level:
        user = await _get_user(session, current_user_id)
        if not user or not getattr(user, "invited_by", None):
            break

        inviter_id = user.invited_by
        amount = line_payouts.get(level)
        if amount:
            session.add(
                Bonus(
                    user_id=inviter_id,
                    payer_id=payer_id,
                    deal_id=None,
                    level=level,
                    amount=amount,
                    status=BonusStatus.potential,
                    created_at=datetime.utcnow(),
                )
            )

        current_user_id = inviter_id
        level += 1

    await session.commit()


async def process_new_partner(session: AsyncSession, sponsor: User, partner: User):
    """
    Вызывается при добавлении нового партнёра.
    1) Проставляет связь по дереву (invited_by),
    2) Начисляет потенциальные бонусы вверх по цепочке,
    3) Обновляет статусы аплайнов (минимум спонсора).
    """
    # 1) связь
    if not getattr(partner, "invited_by", None):
        partner.invited_by = sponsor.id
        session.add(partner)
        await session.commit()  # чтобы partner.id точно был

    # 2) бонусы по линии
    await accrue_bonus(partner.id, session)

    # 3) статусы аплайнов (пересчёт хотя бы спонсора, можно расширить на всю цепочку)
    current_id = sponsor.id
    for _ in range(10):  # разумный лимит глубины
        u = await _get_user(session, current_id)
        if not u:
            break
        await update_partner_status(u, session)
        if not getattr(u, "invited_by", None):
            break
        current_id = u.invited_by


# ---------------------- Структура и статистика ----------------------

async def get_downline_by_levels(
    session: AsyncSession, user_id: int, max_depth: int = 10
) -> Dict[int, List[User]]:
    """
    Возвращает словарь {уровень: [список пользователей]} для партнёрской структуры.
    """
    levels: Dict[int, List[User]] = {}
    current_level_ids = [user_id]

    for depth in range(1, max_depth + 1):
        if not current_level_ids:
            break

        result = await session.execute(
            select(User).where(User.invited_by.in_(current_level_ids))
        )
        users = result.scalars().all()
        if not users:
            break

        levels[depth] = users
        current_level_ids = [u.id for u in users]

    return levels


async def get_structure_stats(session: AsyncSession, user_id: int) -> dict:
    """
    Возвращает статистику структуры:
    - total_partners: общее число партнёров внизу
    - levels: глубина структуры
    - by_levels: {уровень: количество}
    """
    downline = await get_downline_by_levels(session, user_id, max_depth=10)
    total_partners = sum(len(users) for users in downline.values())
    total_levels = len(downline)

    return {
        "total_partners": total_partners,
        "levels": total_levels,
        "by_levels": {level: len(users) for level, users in downline.items()},
    }


# ---------------------- Хендлеры для бота ----------------------

@router.message(F.text == "📊 Моя структура")
async def my_structure(message: types.Message):
    """Партнёр смотрит статистику своей структуры."""
    async with get_session() as session:
        stats = await get_structure_stats(session, message.from_user.id)

    if not stats or stats["total_partners"] == 0:
        await message.answer("У вас пока нет структуры.")
        return

    text = "📊 Ваша структура:\n\n"
    for lvl, count in stats["by_levels"].items():
        text += f"{lvl} уровень: {count} партнёров\n"

    text += f"\nВсего партнёров: {stats['total_partners']}"
    await message.answer(text)


@router.message(Command("status"))
async def my_status(message: types.Message):
    """Показать текущий статус партнёра."""
    async with get_session() as session:
        user = await session.get(User, message.from_user.id)

    if not user:
        await message.answer("❌ Вы не зарегистрированы в системе.")
        return

    await message.answer(
        f"Ваш текущий статус: <b>{user.status or 'Нет статуса'}</b>",
        parse_mode="HTML",
    )
