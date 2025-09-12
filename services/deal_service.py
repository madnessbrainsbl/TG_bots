
from typing import Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db.models import Lead, Deal, User, Bonus
from services.bonus_service import BONUS_PENDING

async def _get_upline_chain(session: AsyncSession, user_id: int, depth: int = 10):
    """Return list of (level, upline_user_id) starting from level=1 for the direct referrer."""
    chain = []
    current_id = user_id
    level = 1
    while level <= depth:
        q = select(User).where(User.id == current_id)
        res = await session.execute(q)
        user = res.scalar_one_or_none()
        if not user or not user.referrer_id:
            break
        chain.append((level, user.referrer_id))
        current_id = user.referrer_id
        level += 1
    return chain

async def close_lead_as_deal(session: AsyncSession, lead_id: int, amount: int, mlm_levels: Dict[int, int]) -> Deal:
    """Mark lead as deal, create Deal row and fan-out MLM bonuses as PENDING (Потенциал)."""
    # 1) Load lead and owner (lead.owner_id => who created the lead)
    res = await session.execute(select(Lead).where(Lead.id == lead_id))
    lead = res.scalar_one_or_none()
    if not lead:
        raise ValueError("Лид не найден")
    if lead.status == "deal":
        raise ValueError("Лид уже закрыт в сделку")

    # 2) Create deal
    deal = Deal(user_id=lead.user_id, lead_id=lead.id, amount=amount)
    session.add(deal)

    # 3) Update lead status
    lead.status = "deal"

    # 4) Build upline chain starting from the lead owner (partner who brought the lead)
    chain = await _get_upline_chain(session, lead.user_id, depth=max(mlm_levels.keys()))
    # Level-1 is direct referrer of lead.user_id; add also level-0 to owner? business rule: no, bonuses go to uplines
    # Fan-out bonuses
    for level, upline_user_id in chain:
        if level in mlm_levels:
            reward = int(mlm_levels[level])
            b = Bonus(user_id=upline_user_id, deal=deal, amount=reward, level=level, status=BONUS_PENDING)
            session.add(b)

    await session.commit()
    return deal
