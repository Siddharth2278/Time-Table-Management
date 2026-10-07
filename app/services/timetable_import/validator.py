"""Record validation: which extracted rows may become training data.

Low-confidence records never auto-pass: anything below 0.5 confidence, or
with an unreadable day/time, or a blank subject, is rejected for manual
review. Nothing here touches the network or the ML model.
"""
from typing import List, Tuple

from app.services.timetable_import import table_normalizer as norm
from app.services.timetable_import.models import TimetableRecord
from app.utils.helpers import time_to_minutes

MIN_AUTO_CONFIDENCE = 0.5


def validate_records(records: List[TimetableRecord]) -> Tuple[List[TimetableRecord], List[TimetableRecord]]:
    """Split records into (approved, rejected). Never raises."""
    approved: List[TimetableRecord] = []
    rejected: List[TimetableRecord] = []
    for record in records:
        problems = _problems(record)
        if problems:
            record.warnings.extend(problems)
            rejected.append(record)
        else:
            approved.append(record)
    return approved, rejected


def _problems(record: TimetableRecord) -> List[str]:
    problems = []
    if not norm.parse_day(record.day):
        problems.append(f"Unrecognized day '{record.day}'.")
    try:
        start, end = time_to_minutes(record.start), time_to_minutes(record.end)
        if end <= start:
            problems.append("End time must be after start time.")
    except (ValueError, AttributeError, TypeError):
        problems.append("Unreadable start/end time.")
    if not (record.subject or "").strip():
        problems.append("Subject is blank.")
    if record.confidence < MIN_AUTO_CONFIDENCE:
        problems.append(f"Low extraction confidence ({record.confidence:.2f}).")
    return problems


def split_approved(records: List[TimetableRecord]) -> Tuple[List[TimetableRecord], List[TimetableRecord]]:
    """Alias kept for a stable public interface."""
    return validate_records(records)
