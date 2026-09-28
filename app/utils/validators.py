import re

def is_valid_email(email: str) -> bool:
    if not email:
        return True  # optional
    if not isinstance(email, str):
        return False
    email = email.strip()
    if not email or len(email) > 254:
        return False
    pattern = r"^[\w\.\+\-]+@[\w\-]+(\.[\w\-]+)*\.[A-Za-z]{2,}$"
    return re.fullmatch(pattern, email) is not None

def not_empty(value: str) -> bool:
    return bool(isinstance(value, str) and value.strip())
