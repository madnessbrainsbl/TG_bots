# хранение состояний пользователей
user_states = {}

def set_nested_value(data, key, value):
    """Устанавливает значение в словаре по вложенному ключу 'a.b.c'"""
    keys = key.split(".")
    d = data
    for k in keys[:-1]:
        if k.isdigit():
            k = int(k)
            while len(d) <= k:
                d.append({})
            d = d[k]
        else:
            if k not in d or not isinstance(d[k], dict):
                d[k] = {}
            d = d[k]
    last_key = keys[-1]
    if last_key.isdigit():
        last_key = int(last_key)
        while len(d) <= last_key:
            d.append(None)
        d[last_key] = value
    else:
        d[last_key] = value

def get_nested_value(data, key):
    """Получает значение из словаря по вложенному ключу 'a.b.c'"""
    keys = key.split(".")
    d = data
    for k in keys:
        if isinstance(d, list) and k.isdigit():
            k = int(k)
            if k >= len(d):
                return None
            d = d[k]
        elif isinstance(d, dict) and k in d:
            d = d[k]
        else:
            return None
    return d
