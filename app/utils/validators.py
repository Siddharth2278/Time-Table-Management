import re

def is_valid_email(email: str) -> bool:
    if not email:
        return True  # optional
    pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    return re.match(pattern, email) is not None

def not_empty(value: str) -> bool:
    return bool(value and value.strip())
