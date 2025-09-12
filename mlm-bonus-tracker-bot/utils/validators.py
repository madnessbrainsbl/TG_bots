def is_positive_int(text: str) -> bool:
    try:
        return int(text) > 0
    except Exception:
        return False