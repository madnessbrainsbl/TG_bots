"""
MLM: начисление бонусов по аплайну.

Синхронизировано с текущими моделями:
- get_session() из db.__init__
- User, Bonus, BonusStatus из db.models
- уровни и суммы читаем из Settings().MLM_LEVELS (если не задано — используем дефолт)
"""

from __future__ import annotations

import logging
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import Settings
from db import get_session
from db.models import User, Bonus, BonusStatus

log = logging.getLogger(__name__)
settings = Settings()

# Фолбэк, если в .env/конфиге не задано MLM_LEVELS
DEFAULT_LEVELS = {
    1: 1000, 2: 900, 3: 800, 4: 700, 5: 600,
    6: 500, 7: 400, 8: 300, 9: 200, 10: 100,
}


async def _get_uplines(session: AsyncSession, user_id: int, depth: int) -> List[int]:
    """
    Собирает список ID аплайнов сверху вниз (1-й уровень — прямой пригласитель).
    Останавливается раньше, если цепочка прерывается.
    """
    uplines: List[int] = []
    current_id = user_id

    for _ in range(depth):
        result = await session.execute(select(User).where(User.id == current_id))
        user = result.scalar_one_or_none()
        if not user or not user.invited_by:
            break
        uplines.append(user.invited_by)
        current_id = user.invited_by

    return uplines


async def accrue_bonuses(deal_id: int, payer_id: int) -> int:
    """
    Начисляет потенциальные бонусы аплайнам за сделку `deal_id`, совершённую `payer_id`.

    Возвращает количество созданных записей Bonus.
    """
    mlm_levels = settings.MLM_LEVELS or DEFAULT_LEVELS
    created = 0

    async with get_session() as session:
        uplines = await _get_uplines(session, payer_id, depth=len(mlm_levels))
        for level, receiver_id in enumerate(uplines, start=1):
            amount = mlm_levels.get(level)
            if not amount:
                continue

            bonus = Bonus(
                deal_id=deal_id,
                payer_id=payer_id,
                user_id=receiver_id,   # получатель бонуса
                level=level,
                amount=amount,
                status=BonusStatus.potential,
            )
            session.add(bonus)
            created += 1
            log.info(
                "Accrue bonus: deal=%s payer=%s -> receiver=%s level=%s amount=%s",
                deal_id, payer_id, receiver_id, level, amount,
            )

        await session.commit()

    return created
