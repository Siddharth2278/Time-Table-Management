"""Phase 2 requirements bridge: DB requirements + learned profile template.

Reads the current generation requirements straight from the database
models and converts the Phase 1 learned profile into the structural
template/role shape the existing solver consumes. No model calls here.
"""
from typing import Any, Dict, List, Tuple

from app.models import (
    Room, RoomAvailability, Semester, Setting, Subject, Teacher,
    TeacherAvailability, TimeSlot, TimetableEntry, WorkingDay,
)


def collect_requirements(session, semester_id: int) -> Dict[str, Any]:
    """Structured requirements for one semester (read-only)."""
    sem = session.query(Semester).filter(Semester.id == semester_id).first()
    if sem is None:
        raise ValueError(f"Semester id {semester_id} does not exist.")
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

    def _blocks(model, id_column, entity_id):
        return [{
            "day_id": row.day_id, "start": row.start_time, "end": row.end_time,
        } for row in session.query(model).filter(
            id_column == entity_id, model.is_unavailable == True).all()]  # noqa: E712

    def _setting(key, default=""):
        row = session.query(Setting).filter(Setting.key == key).first()
        return row.value if row else default

    fixed = session.query(TimetableEntry).filter(
        TimetableEntry.semester_id == semester_id).all()
    return {
        "semester": {"id": sem.id, "name": sem.name},
        "college": _setting("college_name", ""),
        "department": _setting("department", ""),
        "academic_year": _setting("academic_year", ""),
        "subjects": [{
            "id": s.id, "code": s.code, "name": s.name,
            "type": s.subject_type,
            "required": max(0, int(s.required_lectures_per_week or 0)),
            "duration": int(s.lecture_duration or 60),
            "teacher_id": s.teacher_id, "room_id": s.room_id,
            "room_requirement": s.room_requirement or "Classroom",
        } for s in subjects],
        "teachers": [{
            "id": t.id, "name": t.name,
            "unavailable": _blocks(TeacherAvailability,
                                   TeacherAvailability.teacher_id, t.id),
        } for t in teachers],
        "rooms": [{
            "id": r.id, "name": r.name, "number": r.room_number, "type": r.type,
            "unavailable": _blocks(RoomAvailability,
                                   RoomAvailability.room_id, r.id),
        } for r in rooms],
        "days": [{"id": d.id, "name": d.name} for d in days],
        "slots": [{
            "start": s.start_time, "end": s.end_time,
            "break": bool(s.is_break), "break_name": s.break_name or "",
        } for s in slots],
        "fixed_count": len(fixed),
    }


def learned_to_template(session, learned: Dict[str, Any]) -> Tuple[dict, Dict[int, dict]]:
    """Convert a Phase 1 learned profile into solver template + role map.

    Roles transfer by shape (type/duration/frequency); subject names from
    history are never used as rules. Day names align onto the current
    working calendar; unknown names are ignored.
    """
    from app.services.intelligence.subject_role_mapper import map_roles
    order_names = [d.name for d in session.query(WorkingDay).order_by(
        WorkingDay.sort_order).all()]
    order = {name: i for i, name in enumerate(order_names)}
    template_roles = []
    for key in sorted((learned.get("roles", {}) or {})):
        role = learned["roles"][key]
        days = [d for d in (role.get("preferred_days", []) or []) if d in order]
        template_roles.append({
            "frequency": int(role.get("frequency", 0) or 0),
            "day_count": max(1, int(round(role.get("avg_day_count", 0) or 0))),
            "days": days,
            "day_indexes": sorted(order[d] for d in days),
            "gaps": [g for g in (role.get("gaps", []) or []) if isinstance(g, int)],
            "avg_gap": float(role.get("avg_gap", 0.0) or 0.0),
            "spacing": ("grouped" if role.get("type") == "practical"
                        else "distributed"),
            "period_pref": ("morning" if (role.get("morning_share", 0.5) or 0.5) >= 0.66
                            else "afternoon" if (role.get("morning_share", 0.5) or 0.5) <= 0.33
                            else "mixed"),
            "times": list(role.get("preferred_times", []) or []),
            "practical": role.get("type") == "practical",
            "consecutive_block": bool((role.get("adjacent_pair_rate", 0) or 0) >= 0.5),
            "block_lengths": [],
            "duration": int(role.get("duration", 60) or 60),
            "type_class": role.get("type", "theory"),
        })
    patterns = learned.get("patterns", {}) or {}
    total = max(1, int(learned.get("total_lectures", 0) or 0))
    day_load = patterns.get("daily_load", {}) or {}
    time_load = patterns.get("time_load", {}) or {}
    template = {
        "reference_name": "Learned profile "
                          f"({len(learned.get('sources', []) or [])} file(s))",
        "total_lectures": learned.get("total_lectures", 0),
        "roles": template_roles,
        "day_load_profile": {d: day_load.get(d, 0) / total for d in order_names},
        "time_load_profile": {t: time_load.get(t, 0) / total for t in time_load},
        "break_positions": {"periods_before_break": 0, "periods_after_break": 0},
        "breaks": [],
        "daily_density": patterns.get("average_daily_load", 0.0),
        "morning_share": patterns.get("morning_share", 0.5),
        "free_periods": 0,
        "teacher_load_profile": patterns.get("teacher_workload", {}),
        "room_load_profile": patterns.get("room_usage", {}),
        "practical_block_patterns": [{
            "duration": r["duration"], "period": r["period_pref"],
            "block_lengths": [],
        } for r in template_roles if r["practical"]],
        "first_last": {},
        "working_days": order_names,
    }
    return template, template_roles


def map_requirements_to_roles(requirements: Dict[str, Any],
                              template_roles: List[dict]) -> Dict[int, dict]:
    """Map current subjects onto template roles (shape only, never names)."""
    from app.services.intelligence.subject_role_mapper import map_roles

    class _Subject:
        def __init__(self, item):
            self.id = item["id"]
            self.code = item["code"]
            self.subject_type = item["type"]
            self.lecture_duration = item["duration"]
            self.required_lectures_per_week = item["required"]
            self.room_requirement = item["room_requirement"]

    subjects = [_Subject(item) for item in requirements["subjects"]]
    return map_roles(subjects, template_roles)


def learned_to_reference(learned: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a Phase 1 learned profile into reference-profile shape.

    Lets the existing template/pattern machinery consume learned history
    directly: subjects carry their observed days/times/counts, loads map
    to distributions, and the semester label records the file sources.
    """
    patterns = learned.get("patterns", {}) or {}
    total = max(1, int(learned.get("total_lectures", 0) or 0))
    morning_share = patterns.get("morning_share", 0.5) or 0.5
    morning = int(round(morning_share * total))
    label = "Learned profile ({} file(s))".format(
        len(learned.get("sources", []) or []))
    return {
        "semester": {"id": 0, "name": label},
        "total_lectures": learned.get("total_lectures", 0),
        "subjects": [{
            "code": s.get("code", ""),
            "name": s.get("name", ""),
            "type": s.get("type", "Theory"),
            "duration": s.get("duration", 60),
            "count": s.get("count", 0),
            "days": list(s.get("days", []) or []),
            "times": list(s.get("times", []) or []),
        } for s in (learned.get("subjects", []) or [])],
        "subject_count": len(learned.get("subjects", []) or []),
        "day_distribution": dict(patterns.get("daily_load", {}) or {}),
        "time_distribution": dict(patterns.get("time_load", {}) or {}),
        "morning_lectures": morning,
        "afternoon_lectures": max(0, total - morning),
        "working_days": list((patterns.get("daily_load", {}) or {}).keys()),
        "breaks": [],
        "has_data": bool(learned.get("total_lectures", 0)),
    }
