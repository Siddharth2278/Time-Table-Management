"""Supervised training data from historical timetables.

Positives = lectures that actually occurred. Negatives = valid-but-unused
alternative cells for the same subject (same duration window, enabled day,
no break overlap). Features are STRUCTURAL ONLY (role stats + cell +
context) so they transfer to new subjects; names/codes never enter X.
The same extractor serves training (full-history context) and inference
(partial-placement context).
"""
from typing import Any, Dict, List, Tuple

from app.services.local_agent.schemas import LearningError, LectureRow
from app.services.local_agent.timetable_learner import load_rows
from app.utils.helpers import time_to_minutes

FEATURES_V1 = [
    # NOTE: deliberately no role-identity features (type/duration/frequency
    # aggregates). Ranking happens per subject, so identity features only
    # invite memorization; every feature below varies across candidate
    # cells and transfers to new subjects by construction.
    "day_index_norm",
    "start_norm",
    "morning",
    "min_gap_to_same_subject",
    "consecutive_with_same_subject",
    "position_in_day",
    "gap_from_break_norm",
    "daily_load_norm",
    "teacher_load_share",
    "room_busy_share",
    "day_popularity",
    "time_popularity",
    "morning_align",
]
FEATURE_SCHEMA_VERSION = 4
WEEKDAY_ORDER = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
}
NEGATIVES_PER_POSITIVE = 3


def _day_index(day: str) -> int:
    return WEEKDAY_ORDER.get((day or "").strip().lower(), -1)


def _role_stats(rows: List[LectureRow]) -> Dict[str, Any]:
    """Aggregate structural stats for one subject's rows (no names)."""
    days = sorted({_day_index(r.day) for r in rows if _day_index(r.day) >= 0})
    gaps = [b - a for a, b in zip(days, days[1:])]
    morning = afternoon = 0
    for r in rows:
        try:
            if time_to_minutes(r.start) < 12 * 60:
                morning += 1
            else:
                afternoon += 1
        except (ValueError, AttributeError, TypeError):
            continue
    first = rows[0]
    names = sorted({(r.day or "").strip() for r in rows if (r.day or "").strip()})
    starts = sorted({(r.start or "").strip() for r in rows if (r.start or "").strip()})
    day_counts: Dict[str, int] = {}
    time_counts: Dict[str, int] = {}
    for r in rows:
        day_counts[(r.day or "").strip()] = day_counts.get((r.day or "").strip(), 0) + 1
        time_counts[(r.start or "").strip()] = time_counts.get((r.start or "").strip(), 0) + 1
    return {
        "type_practical": 1 if (first.type or "Theory") != "Theory" else 0,
        "duration": first.duration,
        "frequency": len(rows),
        "days": days,
        "day_names": names,
        "times": starts,
        "gaps": gaps,
        "avg_gap": sum(gaps) / len(gaps) if gaps else 0.0,
        "morning_share": morning / max(1, morning + afternoon),
        "day_count": len(days),
        "day_counts": day_counts,
        "time_counts": time_counts,
    }


def extract_features(role: Dict[str, Any], day_index: int, start_min: int,
                     context: Dict[str, Any], day_name=None,
                     start_str=None) -> List[float]:
    """One structural feature vector. Shared by training and inference.

    The last three features measure fit against the role's observed
    day/time/morning pattern as popularity shares (names stay out of X).
    """
    day_load = context.get("day_load", {})
    teacher_share = context.get("teacher_share", 0.0)
    room_share = context.get("room_share", 0.0)
    placed_days = context.get("placed_days", [])
    day_order = context.get("day_order", {})
    same_gaps = [abs(day_index - d) for d in placed_days]
    consecutive = 1 if any(g == 1 for g in same_gaps) else 0
    role_days = role.get("day_names")
    if day_name is None or not role_days:
        day_pop = 0.5
    else:
        day_pop = float(role.get("day_counts", {}).get(day_name, 0))
    role_times = role.get("times")
    if start_str is None or not role_times:
        time_pop = 0.5
    else:
        time_pop = float(role.get("time_counts", {}).get(start_str, 0))
    total_role = max(1, role.get("frequency", 0))
    cell_morning = 1.0 if start_min < 12 * 60 else 0.0
    morning_align = 1.0 - abs(cell_morning - float(role.get("morning_share", 0.5)))
    return [
        day_index / 6.0 if day_index >= 0 else 0.0,
        start_min / 1440.0,
        cell_morning,
        (min(same_gaps) / 6.0) if same_gaps else 1.0,
        float(consecutive),
        context.get("position_in_day", 0.0),
        context.get("gap_from_break", 1.0),
        min(1.0, day_load.get(day_index, 0) / 10.0),
        max(0.0, min(1.0, teacher_share)),
        max(0.0, min(1.0, room_share)),
        round(day_pop / total_role, 3),
        round(time_pop / total_role, 3),
        round(morning_align, 3),
    ]


def _windows_for_day(slots: List[Tuple[int, int]], duration: int) -> List[Tuple[int, int]]:
    """Contiguous-block windows of exactly `duration` minutes."""
    blocks = []
    for start, end in sorted(slots):
        if end - start <= 0:
            continue
        if blocks and start == blocks[-1][1]:
            blocks[-1] = (blocks[-1][0], end)
        else:
            blocks.append((start, end))
    bounds = sorted({s for s, _ in blocks} | {e for _, e in blocks})
    out = []
    for bstart, bend in blocks:
        for t in bounds:
            if bstart <= t and t + duration <= bend and (t, t + duration) not in out:
                out.append((t, t + duration))
    return sorted(out)


def _overlaps(a_start: int, a_end: int, b_start: int, b_end: int) -> bool:
    """Project overlap rule: existingStart < newEnd and existingEnd > newStart."""
    return a_start < b_end and a_end > b_start


def _busy_maps(rows: List[LectureRow]):
    """Per-teacher / per-room busy intervals: {(name, day_index): [(start, end)]}."""
    teacher_busy: Dict[tuple, list] = {}
    room_busy: Dict[tuple, list] = {}
    day_busy: Dict[int, list] = {}
    for r in rows:
        try:
            day_index = _day_index(r.day)
            start, end = time_to_minutes(r.start), time_to_minutes(r.end)
        except (ValueError, AttributeError, TypeError):
            continue
        if day_index < 0 or end <= start:
            continue
        teacher = (r.teacher or "").strip()
        room = (r.room or "").strip()
        if teacher:
            teacher_busy.setdefault((teacher, day_index), []).append((start, end))
        if room:
            room_busy.setdefault((room, day_index), []).append((start, end))
        day_busy.setdefault(day_index, []).append((start, end))
    return teacher_busy, room_busy, day_busy


def _slot_free(busy: Dict[tuple, list], key: tuple, start: int, end: int) -> bool:
    return not any(_overlaps(start, end, b_start, b_end)
                   for b_start, b_end in busy.get(key, []))


def build_dataset(rows: List[LectureRow], slots: List[Tuple[int, int]] | None = None,
                  day_load: Dict[int, int] | None = None,
                  teacher_share: Dict[str, float] | None = None,
                  room_share: Dict[str, float] | None = None,
                  negatives_per_positive: int = NEGATIVES_PER_POSITIVE,
                  breaks: List[Tuple[int, int]] | None = None,
                  strict_negatives: bool = True,
                  valid_days: set | None = None,
                  exclude_global_overlap: bool = True):
    """Build (X, y, meta) supervised examples from historical rows.

    slots = [(start_min, end_min)] teaching windows (breaks excluded).
    breaks = [(start_min, end_min)] excluded periods (optional extra guard).
    valid_days = allowed weekday indexes (default Mon-Sat, plus Sunday only
    when history itself uses Sunday, so an unavailable Sunday is never
    mislabelled as a "rejected alternative").
    With strict_negatives (default), a negative cell is only used when it is
    a genuine alternative scheduling choice:

    - not already used by the same subject (exact day/start match);
    - the subject's own teacher AND room are both free there (covers
      "occupied by another teacher/room" via shared-resource double booking);
    - no lecture at all overlaps there on that day (covers "occupied by
      another semester", even with different staff/room);
    - it does not overlap a break/unavailable window;
    - the window fits the subject duration inside the teaching slots
      (duration-incompatible cells never enter the candidate list);
    - the day is in valid_days (unavailable days never become negatives).

    Returns X (list of float vectors), y (1/0), meta dict with counts.
    Extra meta keys (skipped_occupied, skipped_unavailable) are additive;
    positives/negatives/subjects/skipped_busy keep their existing meaning.
    """
    slots = slots or [(9 * 60, 17 * 60)]
    day_load = day_load or {}
    teacher_share = teacher_share or {}
    room_share = room_share or {}
    by_code: Dict[str, List[LectureRow]] = {}
    for row in rows:
        by_code.setdefault(row.code.strip(), []).append(row)
    teacher_busy, room_busy, day_busy = _busy_maps(rows)
    breaks = breaks or []
    if valid_days is None:
        observed = set(day_busy)
        valid_days = set(range(7)) if 6 in observed else set(range(6))
    else:
        valid_days = set(valid_days)
    X: List[List[float]] = []
    y: List[int] = []
    positives = negatives = skipped_busy = 0
    skipped_occupied = skipped_unavailable = 0
    for code, group in sorted(by_code.items()):
        role = _role_stats(group)
        used = set()
        for r in group:
            try:
                used.add((_day_index(r.day), time_to_minutes(r.start)))
            except (ValueError, AttributeError, TypeError):
                continue
        for row in group:
            day_index = _day_index(row.day)
            if day_index < 0:
                continue
            try:
                start_min = time_to_minutes(row.start)
            except (ValueError, AttributeError, TypeError):
                continue
            context = {
                "day_load": {d: sum(1 for r in rows if _day_index(r.day) == d)
                             for d in set(_day_index(r.day) for r in rows)},
                "teacher_share": teacher_share.get((row.teacher or "").strip(), 0.0),
                "room_share": room_share.get((row.room or "").strip(), 0.0),
                "placed_days": [d for d in role_days(group) if d != day_index],
                "day_order": {},
                "position_in_day": 0.5,
                "gap_from_break": 1.0,
            }
            X.append(extract_features(role, day_index, start_min, context,
                                      day_name=row.day.strip(),
                                      start_str=row.start.strip()))
            y.append(1)
            positives += 1
            index_to_name = {v: k for k, v in WEEKDAY_ORDER.items()}
            cells = []
            made = 0
            teacher = (row.teacher or "").strip()
            room = (row.room or "").strip()
            for day_i in range(7):
                for start, end in _windows_for_day(slots, row.duration):
                    if (day_i, start) in used:
                        continue
                    if strict_negatives:
                        if day_i not in valid_days:
                            skipped_unavailable += 1
                            continue
                        busy = False
                        if teacher and not _slot_free(
                                teacher_busy, (teacher, day_i), start, end):
                            busy = True
                        if room and not _slot_free(
                                room_busy, (room, day_i), start, end):
                            busy = True
                        if any(_overlaps(start, end, b_start, b_end)
                               for b_start, b_end in breaks):
                            busy = True
                        if busy:
                            skipped_busy += 1
                            continue
                        if exclude_global_overlap and any(
                                _overlaps(start, end, b_start, b_end)
                                for b_start, b_end in day_busy.get(day_i, [])):
                            skipped_occupied += 1
                            continue
                    same_day = 1 if day_i == day_index else 0
                    same_time = 1 if start == start_min else 0
                    cells.append((0 if same_day else (1 if same_time else 2),
                                  day_i, start))
            cells.sort(key=lambda t: (t[0], t[1], t[2]))
            for _, day_i, start in cells[:negatives_per_positive]:
                neg_context = dict(context)
                neg_context["placed_days"] = [
                    d for d in role_days(group) if d != day_i]
                X.append(extract_features(role, day_i, start, neg_context,
                                          day_name=index_to_name.get(day_i, ""),
                                          start_str=_fmt(start)))
                y.append(0)
                made += 1
            negatives += made
    meta = {"positives": positives, "negatives": negatives,
            "subjects": len(by_code), "skipped_busy": skipped_busy,
            "skipped_occupied": skipped_occupied,
            "skipped_unavailable": skipped_unavailable}
    if positives == 0:
        raise LearningError("No usable lectures found for training.")
    return X, y, meta


def role_days(group: List[LectureRow]) -> List[int]:
    """Sorted day indexes used by a subject group."""
    return sorted({_day_index(r.day) for r in group if _day_index(r.day) >= 0})


def load_files_as_dicts(file_paths) -> tuple:
    """Load + normalize timetable files into plain row dicts.

    Structured files (.csv/.json/.xlsx-family) keep the legacy learner
    path byte-for-byte. New formats (.xls/.pdf/images) are extracted via
    the offline timetable_import pipeline into the same dict shape.
    Returns (rows, skipped_total, per_file) with rows as
    {code,name,type,duration,day,start,end,teacher,room,source}.
    Raises LearningError on invalid files; files with zero valid rows
    are reported (not fatal) so multi-file runs can continue.
    """
    from app.services.timetable_import.registry import SUPPORTED_EXTENSIONS
    all_rows: List[Dict[str, Any]] = []
    skipped = 0
    per_file = []
    for path in file_paths:
        suffix = "." + str(path).lower().rsplit(".", 1)[-1] \
            if "." in str(path) else ""
        if suffix in SUPPORTED_EXTENSIONS and suffix not in (
                ".csv", ".xlsx", ".xlsm", ".xltx", ".xltm"):
            rows, skipped_here = _load_via_importer(str(path))
        else:
            rows, skipped_here = load_rows(str(path))
            rows = [{
                "code": row.code, "name": row.name, "type": row.type,
                "duration": row.duration, "day": row.day,
                "start": row.start, "end": row.end,
                "teacher": row.teacher, "room": row.room,
                "source": str(path),
            } for row in rows]
        skipped += skipped_here
        all_rows.extend(rows)
        per_file.append({"file": str(path), "rows": len(rows),
                         "skipped": skipped_here})
    return all_rows, skipped, per_file


def _load_via_importer(path: str):
    """New-format files -> approved records -> row dicts (sanitized source)."""
    from pathlib import Path as _Path
    from app.services.timetable_import.importer import TimetableImporter
    extraction = TimetableImporter.import_file(path)
    dicts, _approved, rejected = TimetableImporter.approved_dicts([extraction])
    label = _Path(path).name  # basenames only; never absolute local paths.
    for row in dicts:
        row["source"] = label
    return dicts, len(rejected)


def _fmt(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"
