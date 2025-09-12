from db.models import Payout
from db.db import session

async def request_payout(user_id: int, amount: float, wallet: str):
    payout = Payout(user_id=user_id, amount=amount, wallet=wallet, status="pending")
    session.add(payout)
    session.commit()
    return payout

async def approve_payout(payout_id: int):
    payout = session.query(Payout).filter_by(id=payout_id).first()
    if payout:
        payout.status = "approved"
        session.commit()
    return payout

async def list_payouts(user_id: int):
    return session.query(Payout).filter_by(user_id=user_id).all()
