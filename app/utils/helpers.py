import re

def time_to_minutes(t: str) -> int:
    """Convert HH:MM to minutes since midnight. Supports H:MM and HH:MM."""
    if not isinstance(t, str):
        raise ValueError(f"Invalid time format: {t!r} (expected HH:MM)")
    t = t.strip()
    m = re.match(r"^(\d{1,2}):(\d{2})$", t)
    if not m:
        raise ValueError(f"Invalid time format: {t} (expected HH:MM)")
    h, mins = int(m.group(1)), int(m.group(2))
    if not (0 <= h < 24 and 0 <= mins < 60):
        raise ValueError(f"Invalid time value: {t}")
    return h * 60 + mins

def minutes_to_time(mins: int) -> str:
    if not isinstance(mins, int) or not (0 <= mins < 24 * 60):
        raise ValueError(f"Invalid minutes value: {mins!r} (expected 0..1439)")
    h = mins // 60
    m = mins % 60
    return f"{h:02d}:{m:02d}"

def do_overlap(existing_start: str, existing_end: str, new_start: str, new_end: str) -> bool:
    """Core overlap rule: existingStart < newEnd AND existingEnd > newStart"""
    es = time_to_minutes(existing_start)
    ee = time_to_minutes(existing_end)
    ns = time_to_minutes(new_start)
    ne = time_to_minutes(new_end)
    return es < ne and ee > ns

def validate_time_range(start: str, end: str):
    try:
        s = time_to_minutes(start)
        e = time_to_minutes(end)
    except (ValueError, AttributeError, TypeError) as ve:
        return False, str(ve)
    if e <= s:
        return False, "End time must be after start time."
    return True, ""

def format_time_range(start: str, end: str) -> str:
    return f"{start}-{end}"
