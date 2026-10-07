"""Strict assistant tool layer over existing application services.

Every tool validates parameters, calls a real service, and returns a small
plain dict. Destructive tools set ``requires_confirmation=True`` and the
service layer enforces an explicit Yes before dispatch.
"""
from typing import Any, Dict, List, Optional

from app.services.local_agent.schemas import LearningError


def _session():
    from app.database import get_session
    return get_session()


def _close(session) -> None:
    try:
        session.close()
    except Exception:
        pass


def _teacher_by_name(session, name: str):
    from app.models import Teacher
    row = session.query(Teacher).filter(
        Teacher.name == (name or "").strip()).first()
    if row is None:
        raise LearningError(f"Teacher '{name}' was not found.")
    return row


def _room_by_name(session, name: str):
    from app.models import Room
    row = session.query(Room).filter(
        Room.name == (name or "").strip()).first()
    if row is None:
        raise LearningError(f"Room '{name}' was not found.")
    return row


def _subject_by_code(session, code: str):
    from app.models import Subject
    row = session.query(Subject).filter(
        Subject.code == (code or "").strip()).first()
    if row is None:
        raise LearningError(f"Subject '{code}' was not found.")
    return row


def _semester_by_name(session, name: str):
    from app.models import Semester
    name = (name or "").strip()
    row = session.query(Semester).filter(Semester.name == name).first()
    if row is None:
        # Accept "4" for "Semester 4".
        row = session.query(Semester).filter(
            Semester.name == f"Semester {name}").first()
    if row is None:
        raise LearningError(f"Semester '{name}' was not found.")
    return row


def tool_generate_timetable(semester: str, mode: str = "fill",
                            planner: str = "trained") -> Dict[str, Any]:
    """Dry-run generation via the trained model + solver. Writes nothing."""
    if mode not in ("fill", "fresh", "replace"):
        raise LearningError("Mode must be fill, fresh or replace.")
    if planner not in ("trained", "template"):
        # The assistant never drives the optional Ollama planner directly;
        # it uses the offline trained/template paths only.
        planner = "trained"
    session = _session()
    try:
        sem = _semester_by_name(session, semester)
        from app.services.local_agent.agent import TimetableAgent
        agent = TimetableAgent()
        result = agent.generate_dry_run(session, sem.id, mode, planner=planner)
        return {"semester": sem.name, "planner": planner,
                "accepted": len(result.accepted),
                "unplaced": len(result.rejected),
                "similarity": round(result.structural_similarity, 2),
                "preview": result.accepted[:10]}
    finally:
        _close(session)


def tool_show_semester_timetable(semester: str) -> Dict[str, Any]:
    session = _session()
    try:
        from app.models import Room, Subject, Teacher, WorkingDay
        from app.services.timetable_service import TimetableService
        sem = _semester_by_name(session, semester)
        entries = TimetableService.get_semester_timetable(session, sem.id)
        out = []
        for e in entries[:50]:
            day = session.query(WorkingDay).filter(
                WorkingDay.id == e.day_id).first()
            sub = session.query(Subject).filter(
                Subject.id == e.subject_id).first()
            out.append({"day": day.name if day else "?",
                        "time": f"{e.start_time}-{e.end_time}",
                        "subject": sub.code if sub else "?"})
        return {"semester": sem.name, "count": len(entries), "entries": out}
    finally:
        _close(session)


def tool_show_today_timetable() -> Dict[str, Any]:
    import datetime
    today = datetime.date.today().strftime("%A")
    session = _session()
    try:
        from app.models import Subject, TimetableEntry, WorkingDay
        day = session.query(WorkingDay).filter(WorkingDay.name == today).first()
        if day is None:
            return {"day": today, "count": 0, "entries": []}
        entries = session.query(TimetableEntry).filter(
            TimetableEntry.day_id == day.id).order_by(
                TimetableEntry.start_time).all()
        out = []
        for e in entries[:50]:
            sub = session.query(Subject).filter(
                Subject.id == e.subject_id).first()
            out.append({"time": f"{e.start_time}-{e.end_time}",
                        "subject": sub.code if sub else "?"})
        return {"day": today, "count": len(entries), "entries": out}
    finally:
        _close(session)


def tool_teacher_free_at(teacher: str, day: str, time: str) -> Dict[str, Any]:
    session = _session()
    try:
        from app.models import TimetableEntry, WorkingDay
        tea = _teacher_by_name(session, teacher)
        day_row = session.query(WorkingDay).filter(
            WorkingDay.name == (day or "").strip()).first()
        if day_row is None:
            raise LearningError(f"Day '{day}' was not found.")
        from app.utils.helpers import time_to_minutes
        try:
            point = time_to_minutes(time)
        except (TypeError, ValueError, AttributeError):
            raise LearningError(f"Time '{time}' is not readable (use HH:MM).")
        busy = []
        for e in session.query(TimetableEntry).filter(
                TimetableEntry.teacher_id == tea.id,
                TimetableEntry.day_id == day_row.id).all():
            try:
                if time_to_minutes(e.start_time) <= point < time_to_minutes(e.end_time):
                    busy.append(f"{e.start_time}-{e.end_time}")
            except (TypeError, ValueError, AttributeError):
                continue
        return {"teacher": tea.name, "day": day_row.name, "time": time,
                "free": not busy, "busy": busy}
    finally:
        _close(session)


def tool_who_unavailable(day: str) -> Dict[str, Any]:
    session = _session()
    try:
        from app.models import Teacher, TeacherAvailability, WorkingDay
        day_row = session.query(WorkingDay).filter(
            WorkingDay.name == (day or "").strip()).first()
        if day_row is None:
            raise LearningError(f"Day '{day}' was not found.")
        rows = session.query(TeacherAvailability).filter(
            TeacherAvailability.day_id == day_row.id,
            TeacherAvailability.is_unavailable == True).all()  # noqa: E712
        names = []
        for r in rows:
            tea = session.query(Teacher).filter(Teacher.id == r.teacher_id).first()
            names.append(f"{tea.name if tea else '?'} ({r.start_time}-{r.end_time})")
        return {"day": day_row.name, "unavailable": names}
    finally:
        _close(session)


def tool_move_lecture(entry_id: int, day: str, start: str, end: str) -> Dict[str, Any]:
    session = _session()
    try:
        from app.models import WorkingDay
        from app.services.timetable_service import TimetableService
        try:
            entry_id = int(entry_id)
        except (TypeError, ValueError):
            raise LearningError("Lecture id must be a number.")
        day_row = session.query(WorkingDay).filter(
            WorkingDay.name == (day or "").strip()).first()
        if day_row is None:
            raise LearningError(f"Day '{day}' was not found.")
        ok, out = TimetableService.move_entry(session, entry_id, day_row.id,
                                              start, end)
        if not ok:
            try:
                reasons = "; ".join(c.message for c in out if c.has_conflict)
            except (TypeError, AttributeError):
                reasons = "Placement was rejected."
            raise LearningError(reasons or "Placement was rejected.")
        return {"moved": entry_id, "day": day_row.name,
                "time": f"{start}-{end}"}
    finally:
        _close(session)


def tool_create_teacher(name: str) -> Dict[str, Any]:
    name = (name or "").strip()
    if not name:
        raise LearningError("Teacher name is required.")
    session = _session()
    try:
        from app.models import Teacher
        if session.query(Teacher).filter(Teacher.name == name).first():
            raise LearningError(f"Teacher '{name}' already exists.")
        row = Teacher(name=name, status="Active")
        session.add(row)
        session.commit()
        return {"created": name, "id": row.id}
    except LearningError:
        raise
    except Exception as e:
        try:
            session.rollback()
        except Exception:
            pass
        raise LearningError(f"Cannot add teacher: {e}")
    finally:
        _close(session)


def tool_create_room(name: str, room_type: str = "Classroom") -> Dict[str, Any]:
    name = (name or "").strip()
    if not name:
        raise LearningError("Room name is required.")
    session = _session()
    try:
        from app.models import Room
        if session.query(Room).filter(Room.name == name).first():
            raise LearningError(f"Room '{name}' already exists.")
        row = Room(name=name, room_number=name, type=room_type or "Classroom",
                   capacity=60, status="Available")
        session.add(row)
        session.commit()
        return {"created": name, "id": row.id}
    except LearningError:
        raise
    except Exception as e:
        try:
            session.rollback()
        except Exception:
            pass
        raise LearningError(f"Cannot add room: {e}")
    finally:
        _close(session)


def tool_create_subject(code: str, name: str, semester: str) -> Dict[str, Any]:
    code, name = (code or "").strip(), (name or "").strip()
    if not code or not name:
        raise LearningError("Subject code and name are required.")
    session = _session()
    try:
        from app.models import Subject
        if session.query(Subject).filter(Subject.code == code).first():
            raise LearningError(f"Subject '{code}' already exists.")
        sem = _semester_by_name(session, semester)
        row = Subject(code=code, name=name, semester_id=sem.id,
                      subject_type="Theory", required_lectures_per_week=3,
                      lecture_duration=60)
        session.add(row)
        session.commit()
        return {"created": code, "id": row.id}
    except LearningError:
        raise
    except Exception as e:
        try:
            session.rollback()
        except Exception:
            pass
        raise LearningError(f"Cannot add subject: {e}")
    finally:
        _close(session)


def tool_find_available_lab(day: str, start: str, end: str) -> Dict[str, Any]:
    session = _session()
    try:
        from app.models import Room, TimetableEntry, WorkingDay
        from app.utils.helpers import time_to_minutes
        day_row = session.query(WorkingDay).filter(
            WorkingDay.name == (day or "").strip()).first()
        if day_row is None:
            raise LearningError(f"Day '{day}' was not found.")
        try:
            s_min, e_min = time_to_minutes(start), time_to_minutes(end)
        except (TypeError, ValueError, AttributeError):
            raise LearningError("Times must look like HH:MM.")
        if e_min <= s_min:
            raise LearningError("End time must be after start time.")
        free = []
        labs = session.query(Room).filter(Room.status == "Available").all()
        labs = [r for r in labs if "lab" in (r.type or "").lower()]
        for lab in labs:
            clash = False
            for e in session.query(TimetableEntry).filter(
                    TimetableEntry.room_id == lab.id,
                    TimetableEntry.day_id == day_row.id).all():
                try:
                    if time_to_minutes(e.start_time) < e_min and \
                            time_to_minutes(e.end_time) > s_min:
                        clash = True
                        break
                except (TypeError, ValueError, AttributeError):
                    continue
            if not clash:
                free.append(lab.name)
        return {"day": day_row.name, "time": f"{start}-{end}", "labs": free}
    finally:
        _close(session)


def tool_show_conflicts() -> Dict[str, Any]:
    session = _session()
    try:
        from app.services.conflict_service import ConflictService
        found = ConflictService.detect_all_conflicts(session)
        return {"count": len(found),
                "conflicts": [c.message for c in found[:20]]}
    finally:
        _close(session)


def tool_explain_placement(entry_id: int) -> Dict[str, Any]:
    session = _session()
    try:
        from app.models import Room, Subject, Teacher, TimetableEntry, WorkingDay
        try:
            entry_id = int(entry_id)
        except (TypeError, ValueError):
            raise LearningError("Lecture id must be a number.")
        e = session.query(TimetableEntry).filter(
            TimetableEntry.id == entry_id).first()
        if e is None:
            raise LearningError(f"Lecture {entry_id} was not found.")
        day = session.query(WorkingDay).filter(WorkingDay.id == e.day_id).first()
        sub = session.query(Subject).filter(Subject.id == e.subject_id).first()
        tea = session.query(Teacher).filter(Teacher.id == e.teacher_id).first()
        roo = session.query(Room).filter(Room.id == e.room_id).first()
        from app.services.conflict_service import ConflictService
        problems = [c.message for c in ConflictService.validate_all(
            session, e.semester_id, e.subject_id, e.teacher_id, e.room_id,
            e.day_id, e.start_time, e.end_time,
            exclude_id=e.id) if c.has_conflict]
        lines = [
            f"Lecture {e.id} ({sub.code if sub else '?'} with "
            f"{tea.name if tea else '?'} in {roo.name if roo else '?'} "
            f"on {day.name if day else '?'} {e.start_time}-{e.end_time}).",
            "Placed by the solver; the trained model only suggested "
            "preferences and never bypasses validation.",
        ]
        lines.append("Current validation: "
                     + ("conflict-free." if not problems
                        else "; ".join(problems)))
        return {"entry": entry_id, "explanation": " ".join(lines)}
    finally:
        _close(session)


def tool_training_status() -> Dict[str, Any]:
    from app.services.local_agent import adaptive
    return adaptive.adaptive_status()


def tool_update_agent() -> Dict[str, Any]:
    from app.services.local_agent import adaptive
    report = adaptive.maybe_retrain(force=False)
    if report is None:
        status = adaptive.adaptive_status()
        return {"retrained": False,
                "pending": status["pending"],
                "min_examples": status["min_examples"]}
    return {"retrained": True, "lectures": report.get("lectures"),
            "backend": report.get("backend", "")}


TOOLS: Dict[str, Dict[str, Any]] = {
    "generate_timetable": {"func": tool_generate_timetable,
                           "confirmation": False},
    "show_semester_timetable": {"func": tool_show_semester_timetable,
                                "confirmation": False},
    "show_today_timetable": {"func": tool_show_today_timetable,
                             "confirmation": False},
    "teacher_free_at": {"func": tool_teacher_free_at, "confirmation": False},
    "who_unavailable": {"func": tool_who_unavailable, "confirmation": False},
    "move_lecture": {"func": tool_move_lecture, "confirmation": False},
    "create_teacher": {"func": tool_create_teacher, "confirmation": False},
    "create_room": {"func": tool_create_room, "confirmation": False},
    "create_subject": {"func": tool_create_subject, "confirmation": False},
    "find_available_lab": {"func": tool_find_available_lab,
                           "confirmation": False},
    "show_conflicts": {"func": tool_show_conflicts, "confirmation": False},
    "explain_placement": {"func": tool_explain_placement,
                          "confirmation": False},
    "training_status": {"func": tool_training_status, "confirmation": False},
    "update_agent": {"func": tool_update_agent, "confirmation": False},
}


def dispatch(tool: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Call a tool by name with validated params. Unknown tools rejected."""
    spec = TOOLS.get(tool)
    if spec is None:
        raise LearningError(f"Unknown assistant action '{tool}'.")
    func = spec["func"]
    if not isinstance(params, dict):
        raise LearningError("Assistant action parameters are invalid.")
    try:
        return func(**{k: v for k, v in params.items()})
    except TypeError as e:
        raise LearningError(f"Assistant action '{tool}' got bad arguments: {e}")


def destructive_tool_names() -> List[str]:
    """Tools handled outside this module that need explicit confirmation."""
    return ["clear_timetable", "clear_teachers", "clear_rooms",
            "delete_subjects", "replace_timetable", "restore_backup"]


def needs_confirmation(tool: str) -> bool:
    spec = TOOLS.get(tool)
    if spec is not None:
        return bool(spec.get("confirmation"))
    return tool in destructive_tool_names()
