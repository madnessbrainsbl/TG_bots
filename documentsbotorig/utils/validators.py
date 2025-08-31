import re
from dateutil.parser import parse as parse_date

def validate_field(value, field_type):
    """Проверка значения по типу поля"""
    if field_type == "number":
        return re.match(r"^-?\d+(\.\d+)?$", str(value)) is not None
    elif field_type == "date":
        try:
            parse_date(value)
            return True
        except Exception:
            return False
    elif field_type == "email":
        return re.match(r"^[^@]+@[^@]+\.[^@]+$", str(value)) is not None
    elif field_type == "phone":
        return re.match(r"^\+?\d{10,15}$", str(value)) is not None
    elif field_type == "array":
        return isinstance(value, list)
    elif field_type in ["string", "multiline", "select", "bool", "name"]:
        return True
    return False
