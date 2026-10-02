"""Candidate generation: bounded (day, time, teacher, room) options per lecture."""
from typing import Any, Dict, List

from app.models import Room, Teacher, TimeSlot, WorkingDay
from app.utils.helpers import time_to_minutes

MAX_CANDIDATES_PER_LECTURE = 120
MAX_STAFF_PER_CELL = 3


def slot_windows_for_duration(slots, duration: int) -> List[tuple]:
    """Teaching windows fitting exactly `duration` minutes.

    Contiguous enabled non-break slots merge into blocks; every window
    starts at a real slot boundary and spans exactly duration minutes
    inside one block. Handles 30/45/60/90/120-minute durations against
    the real slot grid, so a 120-minute lab becomes one 09:00-11:00
    block, never a 60-minute row. Returns sorted [(start, end)].
    """
    try:
        duration = int(duration or 60)
    except (TypeError, ValueError):
        duration = 60
    if duration <= 0:
        duration = 60
    segs = []
    for slot in slots:
        try:
            if bool(getattr(slot, "is_break", False)):
                continue
            start, end = slot.start_time.strip(), slot.end_time.strip()
            smin = time_to_minutes(start)
            emins = time_to_minutes(end)
        except (ValueError, AttributeError, TypeError):
            continue
        if emins - smin <= 0:
            continue
        segs.append((smin, emins))
    segs.sort()
    blocks = []
    for smin, emins in segs:
        if blocks and smin == blocks[-1][1]:
            blocks[-1] = (blocks[-1][0], emins)
        else:
            blocks.append((smin, emins))
    starts = {s for s, _ in segs}
    windows = []
    for bstart, bend in blocks:
        for t in sorted(starts):
            if t >= bstart and t + duration <= bend:
                windows.append((_fmt(t), _fmt(t + duration)))
    return sorted(set(windows))


def _fmt(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def _pools(session, subject):
    teachers = session.query(Teacher).filter(
        Teacher.status == "Active").order_by(Teacher.name).all()
    rooms = session.query(Room).filter(
        Room.status == "Available").order_by(Room.name).all()
    teacher_ids = [t.id for t in teachers]
    teacher_order = []
    if subject.teacher_id in teacher_ids:
        teacher_order.append(subject.teacher_id)
    teacher_order += [t for t in teacher_ids if t not in teacher_order]
    room_ids = [r.id for r in rooms]
    room_order = []
    if subject.room_id in room_ids:
        room_order.append(subject.room_id)
    need = (subject.room_requirement or "").strip()
    room_order += [r.id for r in rooms
                   if r.id not in room_order and (not need or r.type == need)]
    room_order += [r.id for r in rooms if r.id not in room_order]
    return teacher_order, room_order


def _cells(session, patterns, duration: int):
    days = session.query(WorkingDay).filter(
        WorkingDay.is_enabled == True).order_by(WorkingDay.sort_order).all()  # noqa: E712
    slots = session.query(TimeSlot).filter(
        TimeSlot.is_enabled == True, TimeSlot.is_break == False  # noqa: E712
    ).order_by(TimeSlot.start_time).all()
    windows = slot_windows_for_duration(slots, duration)
    if not windows:
        return []
    day_rank = {name: i for i, name in enumerate(patterns.get("preferred_days", []))}
    time_rank = {t: i for i, t in enumerate(patterns.get("preferred_times", []))}
    cells = []
    for day in days:
        for start, end in windows:
            cells.append((
                day_rank.get(day.name, len(day_rank)),
                time_rank.get(start, len(time_rank)),
                day.sort_order, start,
                day.id, start, end,
            ))
    cells.sort(key=lambda c: (c[0], c[1], c[2], c[3]))
    return [(day_id, start, end) for _, _, _, _, day_id, start, end in cells]


def generate_candidates(session, subject, patterns, role=None) -> List[Dict[str, Any]]:
    """Ordered candidate placements for ONE lecture of subject (bounded).

    Time ranges always span exactly the subject's lecture_duration, so a
    120-minute lab is proposed as one 09:00-11:00 block, never squeezed
    into a 60-minute slot. When a template role is given, its reference
    days order first so structure transfers instead of scattering.
    """
    try:
        duration = int(subject.lecture_duration or 60)
    except (TypeError, ValueError):
        duration = 60
    teacher_order, room_order = _pools(session, subject)
    if not teacher_order or not room_order:
        return []
    biased = dict(patterns or {})
    if role and role.get("days"):
        biased = dict(biased)
        biased["preferred_days"] = list(role["days"]) + [
            d for d in biased.get("preferred_days", []) if d not in role["days"]]
    out = []
    # Cells outer (best structural cells first), bounded staff combos per
    # cell: assigned teacher/room always included, tail cells still reached.
    for day_id, start, end in _cells(session, biased, duration):
        for teacher_id in teacher_order[:MAX_STAFF_PER_CELL]:
            for room_id in room_order[:MAX_STAFF_PER_CELL]:
                out.append({
                    "subject_id": subject.id,
                    "teacher_id": teacher_id,
                    "room_id": room_id,
                    "day_id": day_id,
                    "start_time": start,
                    "end_time": end,
                    "lecture_type": subject.subject_type or "Theory",
                })
                if len(out) >= MAX_CANDIDATES_PER_LECTURE:
                    return out
    return out
