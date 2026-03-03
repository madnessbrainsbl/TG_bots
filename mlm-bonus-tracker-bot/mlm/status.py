# Bot/mlm/status.py

"""
Логика партнёрских статусов.
Берём план статусов из .env (STATUS_PLAN), если он определён,
иначе используем дефолтный список.
"""

from typing import List, Tuple
from config import settings

# ---------------------- Дефолтный план ----------------------

DEFAULT_STATUS_PLAN: List[Tuple[int, str, int]] = [
    (461, "Элитный", 10000),
    (371, "Бриллиант", 9500),
    (291, "Сапфир", 9000),
    (221, "Платина+", 8500),
    (161, "Платина", 8000),
    (111, "Золото+", 7500),
    (71,  "Золото", 7000),
    (41,  "Серебро+", 6500),
    (21,  "Серебро", 6000),
    (11,  "Бронза+", 5500),
    (0,   "Бронза", 5000),
]

# ---------------------- Вспомогательные функции ----------------------

def get_status_plan() -> List[Tuple[int, str, int]]:
    """
    Возвращает план статусов.
    Если STATUS_PLAN есть в .env → используем его.
    Иначе → возвращаем DEFAULT_STATUS_PLAN.
    """
    return settings.STATUS_PLAN if settings.STATUS_PLAN else DEFAULT_STATUS_PLAN


def get_user_status(points: int) -> str:
    """
    Возвращает название статуса по количеству баллов (status_points).
    """
    plan = get_status_plan()
    for min_points, title, _ in plan:
        if points >= min_points:
            return title
    return "Без статуса"


def compute_status(deals_count: int) -> Tuple[str, int]:
    """
    Возвращает (название статуса, client_price) по количеству подтверждённых сделок.
    """
    plan = sorted(get_status_plan(), key=lambda x: x[0], reverse=True)
    for threshold, name, price in plan:
        if deals_count >= threshold:
            return name, price
    return "-", 0
