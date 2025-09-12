from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from db.models import Referral, Bonus, User
import datetime

MLM_LEVELS = {1: 10, 2: 5, 3: 3, 4: 2, 5: 1}

async def add_referral(session: AsyncSession, sponsor_id: int, partner_id: int):
    for level in range(1, len(MLM_LEVELS) + 1):
        ref = Referral(sponsor_id=sponsor_id, partner_id=partner_id, level=level)
        session.add(ref)
    await session.commit()

async def get_downline_level_counts(session: AsyncSession, user_id: int):
    result = {}
    for level in MLM_LEVELS.keys():
        q = await session.execute(select(Referral).where(Referral.sponsor_id == user_id, Referral.level == level))
        result[level] = len(q.scalars().all())
    return result

async def calculate_personal_stats(session: AsyncSession, user_id: int):
    q = await session.execute(select(User).where(User.id == user_id))
    user = q.scalar_one_or_none()
    return {
        "deals": len(user.deals),
        "bonuses": sum(b.amount for b in user.bonuses),
        "payouts": sum(p.amount for p in user.payouts)
    }

async def calculate_global_stats(session: AsyncSession):
    q = await session.execute(select(User))
    users = q.scalars().all()
    return {
        "users": len(users)
    }

async def accrue_depth_bonuses(session: AsyncSession, deal_id: int, owner_id: int, amount: float):
    for level, percent in MLM_LEVELS.items():
        sponsor_id = owner_id  # в реальности надо доставать цепочку аплайнов
        bonus = Bonus(user_id=sponsor_id, amount=amount * percent / 100, level=level)
        session.add(bonus)
    await session.commit()
