"""Proposal quality evaluation from real system data (never invented).

Compares a generated proposal against the live database: conflicts (always
re-checked), teacher workload, room usage, daily distribution, subject
spacing and structural similarity. The solver enforces hard constraints;
the trained model only ever suggested preferences.
"""
from typing import Any, Dict, List


def evaluate_proposal(session, accepted: List[dict],
                      similarity: float = 0.0) -> Dict[str, Any]:
    """Evaluate accepted entries. Read-only; never writes."""
    from app.models import Room, Subject, Teacher, WorkingDay
    from app.services.conflict_service import ConflictService
    conflicts = 0
    for e in accepted:
        try:
            problems = [c for c in ConflictService.validate_all(
                session, e.get("semester_id", 0) or 0,
                e["subject_id"], e["teacher_id"], e["room_id"],
                e["day_id"], e["start_time"], e["end_time"],
                exclude_id=None, check_subject_limit=False)
                if c.has_conflict]
            conflicts += len(problems)
        except (KeyError, TypeError, AttributeError):
            conflicts += 1
    teacher_load: Dict[str, int] = {}
    room_use: Dict[str, int] = {}
    daily: Dict[str, int] = {}
    spacing: Dict[str, List[str]] = {}
    for e in accepted:
        try:
            teacher = session.query(Teacher).filter(
                Teacher.id == e["teacher_id"]).first()
            room = session.query(Room).filter(
                Room.id == e["room_id"]).first()
            day = session.query(WorkingDay).filter(
                WorkingDay.id == e["day_id"]).first()
            sub = session.query(Subject).filter(
                Subject.id == e["subject_id"]).first()
        except Exception:
            continue
        teacher_load[teacher.name if teacher else "?"] = \
            teacher_load.get(teacher.name if teacher else "?", 0) + 1
        room_use[room.name if room else "?"] = \
            room_use.get(room.name if room else "?", 0) + 1
        daily[day.name if day else "?"] = \
            daily.get(day.name if day else "?", 0) + 1
        if sub is not None:
            spacing.setdefault(sub.code, []).append(
                f"{day.name if day else '?'} {e.get('start_time', '')}")
    return {
        "accepted": len(accepted),
        "conflicts": conflicts,
        "teacher_workload": dict(sorted(teacher_load.items())),
        "room_usage": dict(sorted(room_use.items())),
        "daily_distribution": dict(sorted(daily.items())),
        "subject_spacing": {k: sorted(v) for k, v in sorted(spacing.items())},
        "structural_similarity": round(float(similarity or 0.0), 2),
    }


def summary_lines(report: Dict[str, Any]) -> List[str]:
    """Human-readable lines for UI display."""
    lines = [f"Conflicts re-checked: {report.get('conflicts', 0)}."]
    workload = report.get("teacher_workload", {}) or {}
    if workload:
        top = sorted(workload.items(), key=lambda kv: (-kv[1], kv[0]))[:3]
        lines.append("Heaviest teachers: " +
                     ", ".join(f"{name} ({n})" for name, n in top) + ".")
    daily = report.get("daily_distribution", {}) or {}
    if daily:
        lines.append("Daily load: " +
                     ", ".join(f"{day} {n}" for day, n in sorted(daily.items()))
                     + ".")
    rooms = report.get("room_usage", {}) or {}
    if rooms:
        lines.append(f"Rooms used: {len(rooms)}.")
    lines.append(f"Structural similarity: "
                 f"{report.get('structural_similarity', 0.0):.2f}.")
    return lines
