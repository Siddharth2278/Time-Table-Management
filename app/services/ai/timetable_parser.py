"""Strict validation of AI timetable output.

- Accepts JSON only (a single ```json fence is tolerated, prose is not).
- Every entry is type/shape-checked; unknown ids and bad times are rejected.
- Anything malformed raises AIError and NOTHING is written to the database.
"""
import json
import re
from typing import Any, Dict

from app.services.ai.ai_client import AIError
from app.utils.helpers import time_to_minutes

LECTURE_TYPES = {"Theory", "Practical", "Lab", "Tutorial"}
_TIME_RE = re.compile(r"^\d{2}:\d{2}$")


def _strict_int(value, field):
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise AIError(f"Invalid AI output: '{field}' must be a positive id.")
    return value


def _strict_time(value, field):
    if not isinstance(value, str) or not _TIME_RE.match(value):
        raise AIError(f"Invalid AI output: '{field}' must be HH:MM.")
    try:
        time_to_minutes(value)
    except (ValueError, AttributeError, TypeError):
        raise AIError(f"Invalid AI output: bad time in '{field}'.")
    return value


def extract_json(text: str) -> dict:
    """Parse strict JSON, tolerating one markdown fence. Nothing else."""
    if not isinstance(text, str) or not text.strip():
        raise AIError("Invalid AI output: empty response.")
    cleaned = text.strip()
    fence = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", cleaned, re.DOTALL)
    if fence:
        cleaned = fence.group(1)
    try:
        data = json.loads(cleaned)
    except (ValueError, TypeError):
        raise AIError("Invalid AI output: not valid JSON.")
    if not isinstance(data, dict):
        raise AIError("Invalid AI output: top level must be an object.")
    return data


def _choices_text(response: dict) -> str:
    try:
        return response["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError, AttributeError):
        raise AIError("Invalid AI output: unexpected response shape.")


def parse_proposal(response: dict, semester_id: int,
                   known: dict) -> Dict[str, Any]:
    """Validate AI output against known ids. Returns clean proposal.

    known = {"subjects": set, "teachers": set, "rooms": set, "days": set}.
    Unknown ids and bad rows are dropped into notes (never saved blindly).
    """
    data = extract_json(_choices_text(response))
    if data.get("semester_id") != semester_id:
        raise AIError("Invalid AI output: semester mismatch.")
    raw_entries = data.get("entries")
    if not isinstance(raw_entries, list):
        raise AIError("Invalid AI output: 'entries' must be a list.")
    entries = []
    dropped = []
    for i, row in enumerate(raw_entries):
        try:
            if not isinstance(row, dict):
                raise AIError("row")
            sid = _strict_int(row.get("subject_id"), "subject_id")
            tid = _strict_int(row.get("teacher_id"), "teacher_id")
            rid = _strict_int(row.get("room_id"), "room_id")
            did = _strict_int(row.get("day_id"), "day_id")
            start = _strict_time(row.get("start_time"), "start_time")
            end = _strict_time(row.get("end_time"), "end_time")
            if time_to_minutes(end) <= time_to_minutes(start):
                raise AIError("time order")
            ltype = row.get("lecture_type", "Theory")
            if ltype not in LECTURE_TYPES:
                raise AIError("lecture_type")
            if (sid not in known["subjects"] or tid not in known["teachers"]
                    or rid not in known["rooms"] or did not in known["days"]):
                raise AIError("unknown id")
            entries.append({
                "subject_id": sid, "teacher_id": tid, "room_id": rid,
                "day_id": did, "start_time": start, "end_time": end,
                "lecture_type": ltype,
            })
        except AIError as e:
            dropped.append(f"Row {i}: {e}")
    unplaced = data.get("unplaced", [])
    if not isinstance(unplaced, list):
        raise AIError("Invalid AI output: 'unplaced' must be a list.")
    explanation = data.get("explanation", "")
    if not isinstance(explanation, str):
        raise AIError("Invalid AI output: 'explanation' must be text.")
    return {"semester_id": semester_id, "entries": entries,
            "unplaced": unplaced, "explanation": explanation,
            "dropped": dropped}
