from datetime import datetime, timezone, timedelta

MOSCOW_TZ = timezone(timedelta(hours=3))


def now_moscow() -> datetime:
    """Возвращает datetime в часовом поясе Москвы"""
    return datetime.now(MOSCOW_TZ)


def now_moscow_hhmm() -> str:
    """Возвращает текущее время в Москве в формате ЧЧ:ММ"""
    return now_moscow().strftime("%H:%M")


def now_moscow_full() -> str:
    """Возвращает текущее время в Москве в полном формате (ГГГГ-ММ-ДД ЧЧ:ММ:СС)"""
    return now_moscow().strftime("%Y-%m-%d %H:%M:%S")


def now_moscow_str(fmt: str = "%d.%m.%Y %H:%M") -> str:
    """Возвращает текущее время в Москве в строковом формате (по умолчанию ДД.ММ.ГГГГ ЧЧ:ММ)"""
    return now_moscow().strftime(fmt)
