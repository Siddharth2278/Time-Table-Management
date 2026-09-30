"""Reference timetable analysis: real counts and distributions, read-only."""
from typing import Any, Dict

from app.models import Semester, Subject, TimeSlot, TimetableEntry, WorkingDay
from app.utils.helpers import time_to_minutes


def _day_name(session, day_id):
    day = session.query(WorkingDay).filter(WorkingDay.id == day_id).first()
    return day.name if day else f"Day {day_id}"


def analyze_reference(session, semester_id: int) -> Dict[str, Any]:
    """Structured ReferenceProfile of an existing timetable (possibly empty)."""
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

    subjects: Dict[str, Dict[str, Any]] = {}
    day_dist: Dict[str, int] = {}
    time_dist: Dict[str, int] = {}
    teacher_load: Dict[str, int] = {}
    room_load: Dict[str, int] = {}
    practical = 0
    by_day_subject: Dict[int, Dict[int, list]] = {}
    first_last: Dict[str, Dict[str, str]] = {}
    for e in entries:
        sub = session.query(Subject).filter(Subject.id == e.subject_id).first()
        code = sub.code if sub else f"Sub {e.subject_id}"
        info = subjects.setdefault(code, {
            "code": code, "name": sub.name if sub else "",
            "type": sub.subject_type if sub else e.lecture_type,
            "duration": sub.lecture_duration if sub else None, "count": 0,
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
        by_day_subject.setdefault(e.day_id, {}).setdefault(e.subject_id, []).append(
            (e.start_time, e.lecture_type or "Theory"))
        try:
            mins = time_to_minutes(e.start_time)
            slot = first_last.setdefault(day_name, {"first": e.start_time, "first_mins": mins,
                                                     "last": e.end_time, "last_mins": time_to_minutes(e.end_time)})
            if mins < slot["first_mins"]:
                slot["first"], slot["first_mins"] = e.start_time, mins
            emins = time_to_minutes(e.end_time)
            if emins > slot["last_mins"]:
                slot["last"], slot["last_mins"] = e.end_time, emins
        except (ValueError, AttributeError, TypeError):
            pass

    consecutive_practicals = 0
    for per_subject in by_day_subject.values():
        for pairs in per_subject.values():
            practical_times = [t for t, ty in pairs if ty != "Theory"]
            if len(practical_times) < 2:
                continue
            try:
                ordered = sorted(time_to_minutes(t) for t in practical_times)
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
        "average_daily_lectures": round(len(entries) / max(1, len(day_dist)), 2) if day_dist else 0.0,
        "min_daily_load": min(loads),
        "max_daily_load": max(loads),
        "free_periods": max(0, cells - len(entries)),
        "density": round(len(entries) / cells, 3),
        "teacher_load": teacher_load,
        "room_load": room_load,
        "first_last": {d: {"first": v["first"], "last": v["last"]} for d, v in first_last.items()},
        "has_data": len(entries) > 0,
    }
