from typing import List, Optional, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update

from db.models import Bonus, User, BonusStatus
from mlm.tree import accrue_bonus as tree_accrue_bonus, update_partner_status


# ---------------------- Начисление бонусов ----------------------

async def accrue_bonus(session: AsyncSession, user_id: int, amount: int = 0):
    """
    Обёртка для начисления бонусов при подтверждении сделки.
    - amount оставлен для совместимости.
    - вызывает accrue_bonus из mlm.tree (начисление по линиям).
    - обновляет статус партнёра (Бронза → Серебро → Золото и т.д.).
    """
    user = await session.get(User, user_id)
    if not user:
        return

    # Пересчёт статуса партнёра
    await update_partner_status(user, session)

    # Начисление бонусов по дереву
    await tree_accrue_bonus(user_id, session)


# ---------------------- Операции с бонусами ----------------------

async def list_user_bonuses(session: AsyncSession, user_id: int, limit: int = 50) -> List[Bonus]:
    q = (
        select(Bonus)
        .where(Bonus.user_id == user_id)
        .order_by(Bonus.id.desc())
        .limit(limit)
    )
    res = await session.execute(q)
    return list(res.scalars().all())


async def totals_by_status(session: AsyncSession, user_id: int) -> Dict[str, int]:
    q = (
        select(Bonus.status, func.coalesce(func.sum(Bonus.amount), 0))
        .where(Bonus.user_id == user_id)
        .group_by(Bonus.status)
    )
    res = await session.execute(q)
    rows = res.all()
    totals = {status.value: int(total or 0) for status, total in rows}
    # гарантируем наличие всех ключей
    for s in BonusStatus:
        totals.setdefault(s.value, 0)
    return totals


async def list_pending_bonuses(session: AsyncSession, limit: int = 100) -> List[Bonus]:
    q = (
        select(Bonus)
        .where(Bonus.status == BonusStatus.PENDING)
        .order_by(Bonus.id.desc())
        .limit(limit)
    )
    res = await session.execute(q)
    return list(res.scalars().all())


async def approve_bonus(session: AsyncSession, bonus_id: int) -> Optional[Bonus]:
    q = (
        update(Bonus)
        .where(Bonus.id == bonus_id, Bonus.status == BonusStatus.PENDING)
        .values(status=BonusStatus.APPROVED)
        .returning(Bonus)
    )
    res = await session.execute(q)
    await session.commit()
    row = res.fetchone()
    return row[0] if row else None


async def reject_bonus(session: AsyncSession, bonus_id: int) -> Optional[Bonus]:
    q = (
        update(Bonus)
        .where(Bonus.id == bonus_id, Bonus.status == BonusStatus.PENDING)
        .values(status=BonusStatus.REJECTED)
        .returning(Bonus)
    )
    res = await session.execute(q)
    await session.commit()
    row = res.fetchone()
    return row[0] if row else None


# ---------------------- Вывод бонусов ----------------------

async def withdraw_bonus(session: AsyncSession, user_id: int, amount: int) -> int:
    """
    Списывает бонусы у пользователя на сумму `amount` (переводит из approved в withdrawn).
    Возвращает фактически списанную сумму.
    """
    q = (
        select(Bonus)
        .where(Bonus.user_id == user_id, Bonus.status == BonusStatus.APPROVED)
        .order_by(Bonus.id.asc())
    )
    res = await session.execute(q)
    bonuses = res.scalars().all()

    remaining = amount
    withdrawn = 0

    for b in bonuses:
        if remaining <= 0:
            break
        take = min(b.amount, remaining)
        b.status = BonusStatus.WITHDRAWN
        withdrawn += take
        remaining -= take

    await session.commit()
    return withdrawn


async def restore_bonus(session: AsyncSession, user_id: int, amount: int) -> int:
    """
    Возвращает пользователю бонусы (переводит из withdrawn обратно в approved).
    Используется при отклонении заявки на вывод.
    """
    q = (
        select(Bonus)
        .where(Bonus.user_id == user_id, Bonus.status == BonusStatus.WITHDRAWN)
        .order_by(Bonus.id.desc())
    )
    res = await session.execute(q)
    bonuses = res.scalars().all()

    remaining = amount
    restored = 0

    for b in bonuses:
        if remaining <= 0:
            break
        take = min(b.amount, remaining)
        b.status = BonusStatus.APPROVED
        restored += take
        remaining -= take

    await session.commit()
    return restored
