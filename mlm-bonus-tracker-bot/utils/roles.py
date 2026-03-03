# Bot/utils/roles.py

"""
Утилиты для работы с партнёрскими статусами.
Для обратной совместимости проксируем функции из mlm/status.py,
чтобы не менять существующие импорты в проекте.
"""

from mlm.status import get_user_status, get_status_plan

def get_user_status(points: int) -> str:
    """
    Возвращает название статуса партнёра по количеству баллов (status_points).
    """
    return get_user_status(points)


def get_status_plan():
    """
    Возвращает план статусов из .env (STATUS_PLAN) или дефолтный.
    """
    return get_status_plan()
