# db/__init__.py

from .db import get_session, init_db
from .models import (
    Base,
    User,
    Lead,
    Deal,
    Bonus,
    Payout,
    News,
    Instruction,
    Review,          # ✅ добавлено
    # ENUMы
    UserRole,
    BonusStatus,
    DealStatus,
    PayoutStatus,
    NewsStatus,
)

__all__ = [
    # инфраструктура
    "get_session",
    "init_db",
    "Base",
    # модели
    "User",
    "Lead",
    "Deal",
    "Bonus",
    "Payout",
    "News",
    "Instruction",
    "Review",        # ✅ добавлено
    # enum'ы
    "UserRole",
    "BonusStatus",
    "DealStatus",
    "PayoutStatus",
    "NewsStatus",
]
