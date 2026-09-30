"""Reference-profile analysis + structured AI payload + prompt.

Everything here is read-only analysis of real database content.
Priority: explicit subject config > ConflictService > reference patterns >
AI inference for gaps only.
"""
from typing import Any, Dict, List

from app.models import (
    Room, RoomAvailability, Semester, Setting, Subject, Teacher,
    TeacherAvailability, TimeSlot, TimetableEntry, WorkingDay,
)
from app.services.conflict_service import ConflictService
from app.utils.helpers import time_to_minutes


def _day_name(session, day_id):
    day = session.query(WorkingDay).filter(WorkingDay.id == day_id).first()
    return day.name if day else f"Day {day_id}"


def build_reference_profile(session, semester_id: int) -> Dict[str, Any]:
    """Structured profile of an existing timetable. Empty but valid when none."""
    sem = session.query(Semester).filter(Semester.id == semester_id).first()
    entries = session.query(TimetableEntry).filter(
        TimetableEntry.semester_id == semester_id).all()
    days = session.query(WorkingDay).filter(
        WorkingDay.is_enabled == True).order_by(WorkingDay.sort_order).all()  # noqa: E712
    slots = session.query(TimeSlot).filter(
        TimeSlot.is_enabled == True, TimeSlot.is_break == False  # noqa: E712
    ).order_by(TimeSlot.start_time).all()
    breaks = session.query(TimeSlot).filter(
        TimeSlot.is_enabled == True, TimeSlot.is_break == True  # noqa: E712
    ).order_by(TimeSlot.start_time).all()

    subjects: Dict[int, Dict[str, Any]] = {}
    day_dist: Dict[str, int] = {}
    time_dist: Dict[str, int] = {}
    teacher_load: Dict[str, int] = {}
    room_load: Dict[str, int] = {}
    practical = 0
    by_day_subject: Dict[int, Dict[int, List[str]]] = {}
    for e in entries:
        sub = session.query(Subject).filter(Subject.id == e.subject_id).first()
        code = sub.code if sub else f"Sub {e.subject_id}"
        info = subjects.setdefault(code, {
            "code": code,
            "name": sub.name if sub else "",
            "type": sub.subject_type if sub else e.lecture_type,
            "duration": sub.lecture_duration if sub else None,
            "count": 0,
        })
        info["count"] += 1
        day_name = _day_name(session, e.day_id)
        day_dist[day_name] = day_dist.get(day_name, 0) + 1
        time_dist[e.start_time] = time_dist.get(e.start_time, 0) + 1
        tname = e.teacher.name if e.teacher else f"Teacher {e.teacher_id}"
        teacher_load[tname] = teacher_load.get(tname, 0) + 1
        rname = e.room.name if e.room else f"Room {e.room_id}"
        room_load[rname] = room_load.get(rname, 0) + 1
        if (e.lecture_type or "Theory") != "Theory":
            practical += 1
        by_day_subject.setdefault(e.day_id, {}).setdefault(e.subject_id, []).append(e.start_time)

    consecutive_practicals = 0
    for per_subject in by_day_subject.values():
        for times in per_subject.values():
            if len(times) < 2:
                continue
            try:
                ordered = sorted(time_to_minutes(t) for t in times)
            except (ValueError, AttributeError, TypeError):
                continue
            for a, b in zip(ordered, ordered[1:]):
                if 0 < b - a <= 70:
                    consecutive_practicals += 1
    morning = afternoon = 0
    for e in entries:
        try:
            if time_to_minutes(e.start_time) < 12 * 60:
                morning += 1
            else:
                afternoon += 1
        except (ValueError, AttributeError, TypeError):
            continue
    cells = max(1, len(days) * max(1, len(slots)))
    loads = sorted(day_dist.values()) if day_dist else [0]
    return {
        "semester": {"id": semester_id, "name": sem.name if sem else ""},
        "total_lectures": len(entries),
        "subjects": sorted(subjects.values(), key=lambda s: (-s["count"], s["code"])),
        "subject_count": len(subjects),
        "practical_sessions": practical,
        "consecutive_practical_pairs": consecutive_practicals,
        "day_distribution": day_dist,
        "time_distribution": time_dist,
        "morning_lectures": morning,
        "afternoon_lectures": afternoon,
        "working_days": [d.name for d in days],
        "breaks": [{"start": b.start_time, "end": b.end_time,
                    "name": b.break_name or "Break"} for b in breaks],
        "slots_per_day": len(slots),
        "average_daily_load": round(len(entries) / max(1, len(day_dist)), 2) if day_dist else 0.0,
        "min_daily_load": min(loads),
        "max_daily_load": max(loads),
        "free_periods": max(0, cells - len(entries)),
        "density": round(len(entries) / cells, 3),
        "teacher_load": teacher_load,
        "room_load": room_load,
        "has_data": len(entries) > 0,
    }


def _availability(session, model, id_column, entity_id):
    blocks = []
    for row in session.query(model).filter(
            id_column == entity_id, model.is_unavailable == True).all():  # noqa: E712
        blocks.append({
            "day": _day_name(session, row.day_id),
            "start": row.start_time, "end": row.end_time,
        })
    return blocks


def build_payload(session, semester_id: int, reference_semester_id: int,
                  mode: str) -> Dict[str, Any]:
    """Structured scheduling input. Relevant data only — never the whole DB."""
    def setting(key, default=""):
        row = session.query(Setting).filter(Setting.key == key).first()
        return row.value if row else default

    sem = session.query(Semester).filter(Semester.id == semester_id).first()
    subjects = session.query(Subject).filter(
        Subject.semester_id == semester_id).order_by(Subject.code).all()
    teachers = session.query(Teacher).filter(
        Teacher.status == "Active").order_by(Teacher.name).all()
    rooms = session.query(Room).filter(
        Room.status == "Available").order_by(Room.name).all()
    days = session.query(WorkingDay).filter(
        WorkingDay.is_enabled == True).order_by(WorkingDay.sort_order).all()  # noqa: E712
    slots = session.query(TimeSlot).filter(
        TimeSlot.is_enabled == True).order_by(TimeSlot.start_time).all()  # noqa: E712
    fixed = session.query(TimetableEntry).filter(
        TimetableEntry.semester_id == semester_id).all()

    def teacher_of(t):
        return {"id": t.id, "name": t.name, "department": t.department or ""}

    payload = {
        "college": setting("college_name", ""),
        "department": setting("department", ""),
        "academic_year": setting("academic_year", ""),
        "mode": mode,
        "semester": {"id": semester_id, "name": sem.name if sem else ""},
        "subjects": [{
            "id": s.id, "code": s.code, "name": s.name,
            "type": s.subject_type,
            "required_per_week": int(s.required_lectures_per_week or 0),
            "duration": int(s.lecture_duration or 60),
            "teacher_id": s.teacher_id, "room_id": s.room_id,
            "room_requirement": s.room_requirement or "Classroom",
        } for s in subjects],
        "teachers": [teacher_of(t) for t in teachers],
        "teacher_availability": {
            t.name: _availability(session, TeacherAvailability,
                                  TeacherAvailability.teacher_id, t.id)
            for t in teachers
        },
        "rooms": [{
            "id": r.id, "name": r.name, "number": r.room_number, "type": r.type,
        } for r in rooms],
        "room_availability": {
            r.name: _availability(session, RoomAvailability,
                                  RoomAvailability.room_id, r.id)
            for r in rooms
        },
        "working_days": [{"id": d.id, "name": d.name} for d in days],
        "slots": [{
            "start": s.start_time, "end": s.end_time, "break": bool(s.is_break),
            "break_name": s.break_name or "",
        } for s in slots],
        "fixed_entries": [{
            "subject_id": e.subject_id, "teacher_id": e.teacher_id,
            "room_id": e.room_id, "day_id": e.day_id,
            "start": e.start_time, "end": e.end_time,
            "type": e.lecture_type,
        } for e in fixed],
        "reference_profile": build_reference_profile(session, reference_semester_id),
    }
    return payload


SYSTEM_PROMPT = """You are a college timetable scheduler. Return STRICT JSON only, no prose.
Schema: {"semester_id": int, "entries": [{"subject_id": int, "teacher_id": int,
"room_id": int, "day_id": int, "start_time": "HH:MM", "end_time": "HH:MM",
"lecture_type": "Theory|Practical|Lab|Tutorial"}], "unplaced": [{"subject_id": int,
"remaining": int, "reason": str}], "explanation": str}
Rules in priority order:
1. Explicit required_per_week counts win. Schedule exactly that many per subject
   (minus fixed_entries already placed in fill mode). Never exceed them.
2. Obey working days, break slots (never schedule on breaks), teacher/room
   availability blocks, room types, and durations.
3. Mirror reference_profile structure: per-subject counts, practical pairing,
   day/time distribution, morning/afternoon balance, density.
4. Use fixed_entries as immovable; never duplicate them.
5. If a requirement cannot be placed validly, list it in unplaced with a reason
   instead of inventing an invalid placement."""


def build_messages(payload: Dict[str, Any]) -> list:
    import json
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": (
            "Generate the timetable for this scheduling request:\n"
            + json.dumps(payload, indent=1))},
    ]
