"""Shared normalization: days, times and grid layouts (no network).

Used by every extractor so CSV, Excel, PDF-text and OCR words converge on
the same canonical records. Safe normalizations only (day abbreviations,
time formats); subject/teacher names are never auto-corrected.
"""
import re
from typing import Dict, List, Optional, Tuple

from app.services.timetable_import.models import TimetableRecord

DAY_ALIASES = {
    "mon": "Monday", "monday": "Monday",
    "tue": "Tuesday", "tues": "Tuesday", "tuesday": "Tuesday",
    "wed": "Wednesday", "wednesday": "Wednesday",
    "thu": "Thursday", "thur": "Thursday", "thurs": "Thursday",
    "thursday": "Thursday",
    "fri": "Friday", "friday": "Friday",
    "sat": "Saturday", "saturday": "Saturday",
    "sun": "Sunday", "sunday": "Sunday",
}

BREAK_WORDS = {"break", "lunch", "recess", "interval", "---", "--", "-"}


def parse_day(text: str) -> str:
    """Canonical day name or '' (never guesses)."""
    if not text:
        return ""
    return DAY_ALIASES.get(text.strip().lower(), "")


def _to_hhmm(hour: str, minute: str = "00", meridiem: str = "") -> Optional[str]:
    try:
        hour_int = int(hour)
        minute_int = int(minute or "00")
    except (TypeError, ValueError):
        return None
    mer = (meridiem or "").strip().lower()
    if mer.startswith("p") and hour_int < 12:
        hour_int += 12
    if mer.startswith("a") and hour_int == 12:
        hour_int = 0
    if not (0 <= hour_int < 24 and 0 <= minute_int < 60):
        return None
    return f"{hour_int:02d}:{minute_int:02d}"


_TIME_RE = re.compile(
    r"(?P<h1>\d{1,2})(?:(?P<sep1>[:.])(?P<m1>\d{2}))?\s*(?P<mer1>[AaPp]\.?[Mm]\.?)?"
    r"\s*(?:-|–|—|\bto\b)\s*"
    r"(?P<h2>\d{1,2})(?:(?P<sep2>[:.])(?P<m2>\d{2}))?\s*(?P<mer2>[AaPp]\.?[Mm]\.?)?"
)


def parse_time_range(text: str) -> Optional[Tuple[str, str]]:
    """Parse '9-10', '09:00-10:00', '9:00 AM - 10:00 AM' -> (start, end)."""
    if not text:
        return None
    match = _TIME_RE.search(text.strip())
    if not match:
        return None
    # A trailing meridiem applies to both ends ("9 - 10 AM").
    mer2 = match.group("mer2") or ""
    mer1 = match.group("mer1") or mer2
    start = _to_hhmm(match.group("h1"), match.group("m1") or "00", mer1)
    end = _to_hhmm(match.group("h2"), match.group("m2") or "00", mer2 or mer1)
    if start is None or end is None:
        return None
    if end <= start:
        return None
    return start, end


def is_break_text(text: str) -> bool:
    return (text or "").strip().lower() in BREAK_WORDS


def looks_like_time(text: str) -> bool:
    return parse_time_range(text or "") is not None


def looks_like_day(text: str) -> bool:
    return bool(parse_day(text or ""))


def _cell_subject(text: str) -> str:
    """Cell text as subject; empty for breaks/headers. Never invents values."""
    cleaned = (text or "").strip()
    if not cleaned or is_break_text(cleaned):
        return ""
    if looks_like_day(cleaned) or looks_like_time(cleaned):
        return ""
    return cleaned


def grid_to_records(grid: List[List[str]], source_file: str,
                    source_page: int = 0,
                    confidence: float = 1.0,
                    semester: str = "") -> Tuple[List[TimetableRecord], List[str]]:
    """Convert a timetable grid (first row = headers) into records.

    Supports days-horizontal (columns are days, first column is time) and
    days-vertical (first column holds days, header holds time ranges).
    Returns (records, warnings).
    """
    warnings: List[str] = []
    records: List[TimetableRecord] = []
    rows = [[(cell or "").strip() for cell in row] for row in grid]
    rows = [row for row in rows if any(cell for cell in row)]
    if len(rows) < 2 or not rows[0] or len(rows[0]) < 2:
        return [], ["No timetable grid detected (need headers plus data)."]
    header = rows[0]
    day_cols = [i for i, cell in enumerate(header) if looks_like_day(cell)]
    time_cols = [i for i, cell in enumerate(header) if looks_like_time(cell)]
    first_col_days = sum(1 for row in rows[1:] if looks_like_day(row[0] if row else ""))
    first_col_times = sum(1 for row in rows[1:] if looks_like_time(row[0] if row else ""))
    if len(day_cols) >= 2 and first_col_times >= 1:
        orientation = "days-horizontal"
    elif len(time_cols) >= 2 and first_col_days >= 1:
        orientation = "days-vertical"
    else:
        return [], ["Could not confidently detect a timetable structure. "
                    "Try a clearer image."]
    if orientation == "days-horizontal":
        days = [parse_day(header[i]) for i in day_cols]
        for row_idx, row in enumerate(rows[1:], start=1):
            span = parse_time_range(row[0] if row else "")
            if span is None:
                continue
            start, end = span
            for col_idx, day in zip(day_cols, days):
                subject = _cell_subject(row[col_idx] if col_idx < len(row) else "")
                if not subject:
                    continue
                records.append(TimetableRecord(
                    day=day, start=start, end=end, subject=subject,
                    semester=semester, source_file=source_file,
                    source_page=source_page, source_row=row_idx,
                    source_col=col_idx, confidence=confidence))
    else:
        day_rows = [(idx, parse_day(row[0])) for idx, row in enumerate(rows[1:], start=1)
                    if looks_like_day(row[0] if row else "")]
        time_headers = [(i, parse_time_range(cell)) for i, cell in enumerate(header)
                        if looks_like_time(cell)]
        for row_idx, day in day_rows:
            row = rows[row_idx]
            for col_idx, span in time_headers:
                if span is None:
                    continue
                start, end = span
                subject = _cell_subject(row[col_idx] if col_idx < len(row) else "")
                if not subject:
                    continue
                records.append(TimetableRecord(
                    day=day, start=start, end=end, subject=subject,
                    semester=semester, source_file=source_file,
                    source_page=source_page, source_row=row_idx,
                    source_col=col_idx, confidence=confidence))
    if not records:
        warnings.append("No timetable data was detected in this file.")
    return records, warnings


def row_dicts_to_records(rows: List[Dict[str, str]], source_file: str,
                         source_page: int = 0) -> Tuple[List[TimetableRecord], List[str]]:
    """Normalize header-based row dicts (layout A/C) using known aliases."""
    from app.services.local_agent.timetable_learner import FIELD_ALIASES
    warnings: List[str] = []
    records: List[TimetableRecord] = []
    for idx, raw in enumerate(rows):
        lowered = {(str(k) or "").strip().lower(): v for k, v in dict(raw).items()}
        found: Dict[str, str] = {}
        for field, aliases in FIELD_ALIASES.items():
            for alias in aliases:
                if alias in lowered and lowered[alias] not in (None, ""):
                    found[field] = str(lowered[alias]).strip()
                    break
            else:
                found[field] = ""
        # Bare "Subject" header means both code and name (common in real files).
        if not found.get("code") and not found.get("name") and "subject" in lowered:
            bare = str(lowered["subject"] or "").strip()
            found["code"] = bare
            found["name"] = bare
        if found.get("break", "").strip().lower() in (
                "1", "true", "yes", "y", "break", "lunch"):
            continue
        day = parse_day(found.get("day", ""))
        range_text = ""
        if found.get("start") or found.get("end"):
            range_text = f"{found.get('start', '')}-{found.get('end', '')}"
        else:
            # Single "Time"/"Slot"/"Timing" column holding a range.
            for key, value in lowered.items():
                if any(token in key for token in
                       ("time", "slot", "timing", "period", "hours", "timings")):
                    if str(value or "").strip():
                        range_text = str(value).strip()
                        break
        span = parse_time_range(range_text)
        if not day or span is None:
            continue
        start, end = span
        subject = (found.get("name") or found.get("code") or "").strip()
        if not subject:
            warnings.append(f"Row {idx + 1}: subject is blank; skipped.")
            continue
        try:
            duration = int(float(found.get("duration") or 0) or 0)
        except (TypeError, ValueError):
            duration = 0
        lecture_type = (found.get("type") or "Theory").strip() or "Theory"
        records.append(TimetableRecord(
            day=day, start=start, end=end, subject=subject,
            teacher=found.get("teacher", ""), room=found.get("room", ""),
            lecture_type=lecture_type,
            is_lab=lecture_type.lower() != "theory",
            source_file=source_file, source_page=source_page,
            source_row=idx, confidence=1.0))
        _ = duration
    if not records:
        warnings.append("No timetable data was detected in this file.")
    return records, warnings


def looks_like_grid(headers: List[str]) -> bool:
    """True when headers look like a timetable grid (days or times)."""
    days = sum(1 for h in headers if looks_like_day(h))
    times = sum(1 for h in headers if looks_like_time(h))
    return days >= 2 or times >= 2


def words_to_records(words: List[Dict[str, object]], source_file: str,
                     source_page: int = 0) -> Tuple[List[TimetableRecord], List[str]]:
    """Reconstruct timetable records from OCR words with bounding boxes.

    Each word is {text, x0, y0, x1, y1, conf}. Works for both orientations:
    days-across-the-top (columns are days) and days-down-the-side
    (columns are time ranges). Returns (records, warnings).
    """
    warnings: List[str] = []
    clean = []
    for word in words:
        text = str(word.get("text", "") or "").strip()
        if not text:
            continue
        try:
            conf = float(word.get("conf", 0) or 0)
        except (TypeError, ValueError):
            conf = 0.0
        clean.append({"text": text,
                      "cx": (float(word.get("x0", 0)) + float(word.get("x1", 0))) / 2,
                      "y0": float(word.get("y0", 0)),
                      "y1": float(word.get("y1", 0)),
                      "conf": max(0.0, min(100.0, conf)) / 100.0})
    if not clean:
        return [], ["No text was detected in this image."]
    heights = sorted(w["y1"] - w["y0"] for w in clean if w["y1"] > w["y0"])
    median_h = heights[len(heights) // 2] if heights else 10.0
    tolerance = max(2.0, median_h * 0.6)
    lines: List[List[Dict[str, object]]] = []
    for word in sorted(clean, key=lambda w: (w["y0"], w["cx"])):
        placed = False
        for line in lines:
            if abs(word["y0"] - line[0]["y0"]) <= tolerance:
                line.append(word)
                placed = True
                break
        if not placed:
            lines.append([word])
    for line in lines:
        line.sort(key=lambda w: w["cx"])
    header_idx = next(
        (i for i, line in enumerate(lines)
         if sum(1 for w in line if looks_like_day(str(w["text"]))) >= 2
         or sum(1 for w in line if looks_like_time(str(w["text"]))) >= 2),
        None)
    if header_idx is None:
        return [], ["Could not confidently detect a timetable structure. "
                    "Try a clearer image."]
    header = lines[header_idx]
    day_tokens = [(w["cx"], parse_day(str(w["text"])))
                  for w in header if looks_like_day(str(w["text"]))]
    time_tokens = [(w["cx"], parse_time_range(str(w["text"])))
                   for w in header if looks_like_time(str(w["text"]))]
    records: List[TimetableRecord] = []
    if len(day_tokens) >= 2:
        columns = sorted(day_tokens, key=lambda t: t[0])
        for line in lines[header_idx + 1:]:
            if not line:
                continue
            span = parse_time_range(str(line[0]["text"]))
            body = line if span is None else line[1:]
            if span is None:
                # Time may be split across tokens ("09:00 - 10:00").
                span = parse_time_range(" ".join(str(w["text"]) for w in line[:4]))
                if span is not None:
                    body = line[4:]
            if span is None:
                continue
            start, end = span
            buckets: Dict[int, List[Dict[str, object]]] = {i: [] for i in range(len(columns))}
            for word in body:
                nearest = min(range(len(columns)),
                              key=lambda i: abs(word["cx"] - columns[i][0]))
                buckets[nearest].append(word)
            for i, (_, day) in enumerate(columns):
                text = " ".join(str(w["text"]) for w in buckets[i]).strip()
                subject = _cell_subject(text)
                if not subject:
                    continue
                confs = [float(w["conf"]) for w in buckets[i] if float(w["conf"]) > 0]
                conf = (sum(confs) / len(confs)) if confs else 0.5
                records.append(TimetableRecord(
                    day=day, start=start, end=end, subject=subject,
                    source_file=source_file, source_page=source_page,
                    confidence=round(conf, 2)))
    elif len(time_tokens) >= 2:
        columns = sorted(time_tokens, key=lambda t: t[0])
        for line in lines[header_idx + 1:]:
            if not line or not looks_like_day(str(line[0]["text"])):
                continue
            day = parse_day(str(line[0]["text"]))
            buckets = {i: [] for i in range(len(columns))}
            for word in line[1:]:
                nearest = min(range(len(columns)),
                              key=lambda i: abs(word["cx"] - columns[i][0]))
                buckets[nearest].append(word)
            for i, (_, span) in enumerate(columns):
                if span is None:
                    continue
                start, end = span
                text = " ".join(str(w["text"]) for w in buckets[i]).strip()
                subject = _cell_subject(text)
                if not subject:
                    continue
                confs = [float(w["conf"]) for w in buckets[i] if float(w["conf"]) > 0]
                conf = (sum(confs) / len(confs)) if confs else 0.5
                records.append(TimetableRecord(
                    day=day, start=start, end=end, subject=subject,
                    source_file=source_file, source_page=source_page,
                    confidence=round(conf, 2)))
    else:
        return [], ["Could not confidently detect a timetable structure. "
                    "Try a clearer image."]
    if not records:
        warnings.append("No timetable data was detected in this file.")
    return records, warnings
