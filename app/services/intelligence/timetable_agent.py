"""Timetable Intelligence orchestrator: fully offline, deterministic.

Pipeline: reference -> requirements -> constraints -> patterns ->
candidates -> optimization -> validation. Dry runs execute inside a
rolled-back transaction (Cancel/discards change nothing). Apply is
all-or-nothing with rollback on any failure.
"""
from typing import Any, Callable, Dict, List, Optional

from app.models import Room, Semester, Subject, Teacher, TimeSlot, WorkingDay
from app.services.conflict_service import ConflictService
from app.services.intelligence.candidate_generator import generate_candidates
from app.services.intelligence.generation_result import (
    diff_proposal, explain_result, pattern_lines,
)
from app.services.intelligence.pattern_extractor import extract_patterns
from app.services.intelligence.subject_role_mapper import map_roles
from app.services.intelligence.timetable_template import template_from_profile
from app.services.intelligence.timetable_scorer import timetable_similarity
from app.services.intelligence.reference_analyzer import analyze_reference
from app.services.intelligence.requirement_analyzer import analyze_requirements
from app.services.intelligence.timetable_optimizer import optimize
from app.services.intelligence.timetable_scorer import score_candidate

STAGES = ["reference", "requirements", "constraints", "patterns",
          "candidates", "optimization", "validation"]


class IntelligenceError(Exception):
    """User-safe failure (displayable message, never a traceback)."""


def _entry_model():
    from app.models import TimetableEntry
    return TimetableEntry


def _existing_tuples(session, semester_id: int) -> List[dict]:
    rows = session.query(_entry_model()).filter(
        _entry_model().semester_id == semester_id).all()
    return [{"day_id": r.day_id, "start_time": r.start_time, "end_time": r.end_time,
             "subject_id": r.subject_id, "teacher_id": r.teacher_id,
             "room_id": r.room_id, "lecture_type": r.lecture_type} for r in rows]


def _to_row(semester_id: int, entry: dict):
    return _entry_model()(
        semester_id=semester_id, subject_id=entry["subject_id"],
        teacher_id=entry["teacher_id"], room_id=entry["room_id"],
        day_id=entry["day_id"], start_time=entry["start_time"],
        end_time=entry["end_time"],
        lecture_type=entry.get("lecture_type") or "Theory")


def _validate_final(session, semester_id: int, entries: List[dict]):
    """Re-validate a finished proposal top to bottom. Returns rejected list."""
    from app.services.intelligence.timetable_optimizer import _room_type_ok
    rejected = []
    for entry in entries:
        problems = [c.message for c in ConflictService.validate_all(
            session, semester_id, entry["subject_id"], entry["teacher_id"],
            entry["room_id"], entry["day_id"], entry["start_time"],
            entry["end_time"], exclude_id=None, check_subject_limit=True)
            if c.has_conflict]
        type_problem = _room_type_ok(session, entry["subject_id"], entry["room_id"])
        if type_problem:
            problems.append(type_problem)
        if problems:
            rejected.append({**entry, "reason": problems[0]})
            continue
        try:
            session.add(_to_row(semester_id, entry))
            session.flush()
        except Exception as e:
            session.rollback()
            raise IntelligenceError(f"Database failure during validation: {e}")
    return rejected


def run_intelligence(session, target_sem_id: int, ref_sem_id: int, mode: str,
                     progress: Optional[Callable[[str], None]] = None,
                     ref_profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Full pipeline. Writes NOTHING (rolled-back dry run).

    ref_profile optionally supplies an EXTERNAL reference (file import)
    instead of a database semester; ref_sem_id is then informational.
    """
    done = progress or (lambda stage: None)
    if mode not in ("fill", "fresh", "replace"):
        raise IntelligenceError("Unknown generation mode.")

    if ref_profile is None:
        profile = analyze_reference(session, ref_sem_id)
    else:
        profile = ref_profile
    if not profile.get("has_data"):
        raise IntelligenceError(
            "Reference timetable is empty. Pick a semester with lectures.")
    done("reference")

    requirements = analyze_requirements(session, target_sem_id)
    if not requirements:
        raise IntelligenceError("Target semester has no subjects.")
    done("requirements")

    teachers = session.query(Teacher).filter(
        Teacher.status == "Active").order_by(Teacher.name).all()
    rooms = session.query(Room).filter(
        Room.status == "Available").order_by(Room.name).all()
    days = session.query(WorkingDay).filter(
        WorkingDay.is_enabled == True).order_by(WorkingDay.sort_order).all()  # noqa: E712
    slots = session.query(TimeSlot).filter(
        TimeSlot.is_enabled == True).order_by(TimeSlot.start_time).all()  # noqa: E712
    if not teachers:
        raise IntelligenceError("No active teachers.")
    if not rooms:
        raise IntelligenceError("No available rooms.")
    if not days:
        raise IntelligenceError("No working days enabled.")
    if not [s for s in slots if not s.is_break]:
        raise IntelligenceError("No teaching slots defined.")
    done("constraints")

    patterns = extract_patterns(profile)
    template = template_from_profile(session, profile, ref_sem_id)
    roles = map_roles([item["subject"] for item in requirements],
                      template.get("roles", []))
    done("patterns")

    existing = _existing_tuples(session, target_sem_id)
    if mode == "fresh" and existing:
        raise IntelligenceError(
            "Semester already has lectures. Use Fill Missing or Replacement Proposal.")
    if mode == "replace":
        for row in session.query(_entry_model()).filter(
                _entry_model().semester_id == target_sem_id).all():
            session.delete(row)
        session.flush()
    try:
        day_names = {d.id: d.name for d in days}
        day_order = {d.id: d.sort_order for d in days}
        if mode == "fill":
            units = []
            for item in requirements:
                # NOTE: distinct dict per lecture; [{"subject": s}] * n would
                # alias one dict and corrupt per-unit placement tracking.
                units += [{"subject": item["subject"]} for _ in range(item["remaining"])]
        else:
            units = []
            for item in requirements:
                units += [{"subject": item["subject"]} for _ in range(item["required"])]
        # Constrained-first: practicals, then largest remaining, then code.
        counts: Dict[int, int] = {}
        for u in units:
            counts[u["subject"].id] = counts.get(u["subject"].id, 0) + 1
        def _order_key(u):
            s = u["subject"]
            practical = 0 if (s.subject_type or "Theory") != "Theory" else 1
            return (practical, -counts[s.id], s.code or "")
        units.sort(key=_order_key)
        # Candidate preview facts (first unit) prove generation ran.
        preview_count = 0
        if units:
            preview_count = len(generate_candidates(
                session, units[0]["subject"], patterns,
                roles.get(units[0]["subject"].id)))
        done("candidates")

        result = optimize(session, target_sem_id, units, patterns, day_names,
                          roles, template, day_order)
        # The optimizer validated every accepted entry through the engine
        # against committed state plus the flushed batch, so the finished
        # set is already authoritative. The finally-block rolls back the
        # whole dry run (nothing is ever committed here).
        accepted = result["accepted"]
        rejected = [{"subject_id": None, "code": u["code"], "name": u["name"],
                     "reason": u["reason"]} for u in result["unplaced"]]
        similarity = timetable_similarity(accepted, template, roles, day_names)
        done("validation")
    finally:
        session.rollback()

    reference_name = profile.get("semester", {}).get("name", "reference")
    return {
        "mode": mode,
        "target_semester_id": target_sem_id,
        "reference": profile,
        "template": template,
        "requirements": [{
            "code": item["subject"].code, "name": item["subject"].name,
            "type": item["subject"].subject_type,
            "required": item["required"], "scheduled": item["scheduled"],
            "remaining": item["remaining"],
        } for item in requirements],
        "candidate_preview_count": preview_count,
        "accepted": accepted,
        "rejected": rejected,
        "diff": diff_proposal(existing, accepted),
        "explanation": explain_result(session, reference_name, accepted, len(rejected))
        + "\n\n" + pattern_lines(template),
        "similarity": similarity,
        "validations": result["validations"],
    }


def apply_result(session, target_sem_id: int, result: Dict[str, Any],
                 mode: str) -> Dict[str, int]:
    """All-or-nothing apply. Rejects anything -> rollback, nothing written."""
    entries = list(result.get("accepted", []))
    try:
        if mode == "replace":
            for row in session.query(_entry_model()).filter(
                    _entry_model().semester_id == target_sem_id).all():
                session.delete(row)
            session.flush()
        rejected = _validate_final(session, target_sem_id, entries)
        if rejected:
            session.rollback()
            return {"applied": 0, "rejected": len(rejected)}
        session.commit()
        return {"applied": len(entries), "rejected": 0}
    except Exception:
        session.rollback()
        raise
