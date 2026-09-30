"""Candidate generation: bounded (day, time, teacher, room) options per lecture."""
from typing import Any, Dict, List

from app.models import Room, Teacher, TimeSlot, WorkingDay

MAX_CANDIDATES_PER_LECTURE = 48


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


def _cells(session, patterns):
    days = session.query(WorkingDay).filter(
        WorkingDay.is_enabled == True).order_by(WorkingDay.sort_order).all()  # noqa: E712
    slots = session.query(TimeSlot).filter(
        TimeSlot.is_enabled == True, TimeSlot.is_break == False  # noqa: E712
    ).order_by(TimeSlot.start_time).all()
    day_rank = {name: i for i, name in enumerate(patterns.get("preferred_days", []))}
    time_rank = {t: i for i, t in enumerate(patterns.get("preferred_times", []))}
    cells = []
    for day in days:
        for slot in slots:
            cells.append((
                day_rank.get(day.name, len(day_rank)),
                time_rank.get(slot.start_time, len(time_rank)),
                day.sort_order, slot.start_time,
                day.id, slot.start_time, slot.end_time,
            ))
    cells.sort(key=lambda c: (c[0], c[1], c[2], c[3]))
    return [(day_id, start, end) for _, _, _, _, day_id, start, end in cells]


def generate_candidates(session, subject, patterns) -> List[Dict[str, Any]]:
    """Ordered candidate placements for ONE lecture of subject (bounded)."""
    teacher_order, room_order = _pools(session, subject)
    if not teacher_order or not room_order:
        return []
    out = []
    for day_id, start, end in _cells(session, patterns):
        for teacher_id in teacher_order:
            for room_id in room_order:
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
