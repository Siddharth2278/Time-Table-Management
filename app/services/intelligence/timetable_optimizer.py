"""Deterministic backtracking optimizer over scored candidates.

- Lectures ordered constrained-first (practicals, then largest remaining).
- Candidates tried in weighted-score order (not first-valid).
- Each attempt validated by the real ConflictService against committed
  state plus already-accepted batch rows (flushed in-transaction).
- Backtracking undoes explicitly (delete + flush): no savepoints, so no
  rolled-back row can ever resurrect and inflate counts.
- A validation budget bounds runtime; leftovers are reported, never faked.
"""
from typing import Any, Dict, List

from app.models import Room, Subject, TimeSlot
from app.services.conflict_service import ConflictService
from app.services.intelligence.candidate_generator import (
    _fmt, generate_candidates, slot_windows_for_duration,
)
from app.services.intelligence.timetable_scorer import score_candidate
from app.utils.helpers import time_to_minutes

BRANCH_LIMIT = 12
DEFAULT_BUDGET = 3000


def _room_type_ok(session, subject_id: int, room_id: int):
    subject = session.query(Subject).filter(Subject.id == subject_id).first()
    room = session.query(Room).filter(Room.id == room_id).first()
    if subject is None or room is None:
        return "Unknown subject or room."
    need = (subject.room_requirement or "").strip().lower()
    if need and need != (room.type or "").strip().lower():
        return f"Room type mismatch: {subject.code} needs {subject.room_requirement}."
    return None


def _to_row(semester_id: int, entry: dict):
    from app.models import TimetableEntry
    return TimetableEntry(
        semester_id=semester_id, subject_id=entry["subject_id"],
        teacher_id=entry["teacher_id"], room_id=entry["room_id"],
        day_id=entry["day_id"], start_time=entry["start_time"],
        end_time=entry["end_time"],
        lecture_type=entry.get("lecture_type") or "Theory")


def _empty_context():
    return {"by_day_subject": {}, "day_load": {}, "teacher_load": {}, "day_names": {}}


def _forget(row, session):
    try:
        session.expunge(row)
    except Exception:
        pass


def optimize(session, semester_id: int, units: List[dict],
             patterns: Dict[str, Any], day_names: Dict[int, str],
             roles: Dict[int, dict], template: dict,
             day_order: Dict[int, int],
             budget: int = DEFAULT_BUDGET,
             plan: Dict[tuple, int] | None = None,
             avoid: set | None = None) -> Dict[str, Any]:
    """Place lecture units. Returns {accepted, unplaced, validations, complete}.

    plan optionally biases scoring toward local-model preferences;
    avoid skips exact (subject_id, day_id, start_time) cells (regeneration).
    Neither can admit an invalid placement: the engine still decides.
    """
    """Place lecture units. Returns {accepted, unplaced, validations, complete}."""
    context = _empty_context()
    context["day_names"] = day_names
    context["day_order"] = day_order
    context["roles"] = roles
    context["template"] = template
    accepted: List[dict] = []
    accepted_rows: List[Any] = []
    unplaced: List[dict] = []
    best: List[dict] = []
    state = {"validations": 0, "stop": False}

    def push_context(candidate):
        day_map = context["by_day_subject"].setdefault(candidate["day_id"], {})
        day_map.setdefault(candidate["subject_id"], []).append(candidate["start_time"])
        context["day_load"][candidate["day_id"]] = context["day_load"].get(candidate["day_id"], 0) + 1
        context["teacher_load"][candidate["teacher_id"]] = context["teacher_load"].get(candidate["teacher_id"], 0) + 1

    def rebuild_context():
        fresh = _empty_context()
        fresh["day_names"] = day_names
        for cand in accepted:
            day_map = fresh["by_day_subject"].setdefault(cand["day_id"], {})
            day_map.setdefault(cand["subject_id"], []).append(cand["start_time"])
            fresh["day_load"][cand["day_id"]] = fresh["day_load"].get(cand["day_id"], 0) + 1
            fresh["teacher_load"][cand["teacher_id"]] = fresh["teacher_load"].get(cand["teacher_id"], 0) + 1
        context.clear()
        context.update(fresh)

    def attempt(candidate):
        """Validate with the engine; flush on success. Returns (ok, reason, row)."""
        if state["validations"] >= budget:
            state["stop"] = True
            return False, "Optimization budget exhausted.", None
        state["validations"] += 1
        problems = [c.message for c in ConflictService.validate_all(
            session, semester_id, candidate["subject_id"], candidate["teacher_id"],
            candidate["room_id"], candidate["day_id"], candidate["start_time"],
            candidate["end_time"], exclude_id=None, check_subject_limit=True)
            if c.has_conflict]
        type_problem = _room_type_ok(session, candidate["subject_id"], candidate["room_id"])
        if type_problem:
            problems.append(type_problem)
        if problems:
            return False, problems[0], None
        row = _to_row(semester_id, candidate)
        session.add(row)
        try:
            session.flush()
        except Exception as e:
            session.rollback()
            raise e
        return True, "", row

    def undo(row):
        """Explicitly remove a branch row (deterministic, no savepoints)."""
        try:
            session.delete(row)
            session.flush()
        except Exception:
            pass
        _forget(row, session)

    def dfs(index: int, work: List[dict]) -> bool:
        nonlocal best
        if state["stop"] or index >= len(work):
            return True
        unit = work[index]
        role = roles.get(unit["subject"].id, {})
        candidates = generate_candidates(session, unit["subject"], patterns, role)
        if avoid:
            candidates = [c for c in candidates
                          if (c["subject_id"], c["day_id"], c["start_time"]) not in avoid]
        scored = sorted(
            ((score_candidate(c, unit["subject"], role, template, context, plan),
              c["day_id"], c["start_time"], c["teacher_id"], c["room_id"], c)
             for c in candidates),
            key=lambda t: (-t[0], t[1], t[2], t[3], t[4]))
        last_reason = "No candidate cells available."
        for _, _, _, _, _, cand in scored[:BRANCH_LIMIT]:
            if state["stop"]:
                break
            try:
                ok, reason, row = attempt(cand)
            except Exception:
                raise
            if ok:
                accepted.append(cand)
                accepted_rows.append(row)
                push_context(cand)
                unit["placed"] = cand
                if len(accepted) > len(best):
                    best = list(accepted)
                if dfs(index + 1, work):
                    return True
                accepted.pop()
                accepted_rows.pop()
                rebuild_context()
                undo(row)
                del unit["placed"]
            else:
                last_reason = reason
        unit["fail_reason"] = last_reason
        return False

    # Phase 1: template-directed direct placement (fast path). Each unit
    # first tries its role's own reference cells with assigned staff, so
    # structure transfers exactly when constraints allow. Leftovers fall
    # through to backtracking search.
    from app.services.intelligence.candidate_generator import _pools
    day_name_to_id = {name: did for did, name in day_names.items()}
    slots = session.query(TimeSlot).filter(
        TimeSlot.is_enabled == True, TimeSlot.is_break == False  # noqa: E712
    ).order_by(TimeSlot.start_time).all()
    windows_cache: Dict[int, set] = {}
    used_cells = set()
    for unit in units:
        if state["stop"]:
            break
        subject = unit["subject"]
        role = roles.get(subject.id, {})
        try:
            duration = int(subject.lecture_duration or 60)
        except (TypeError, ValueError):
            duration = 60
        if duration not in windows_cache:
            windows_cache[duration] = set(slot_windows_for_duration(slots, duration))
        windows = windows_cache[duration]
        teacher_order, room_order = _pools(session, subject)
        attempts = 0
        for day_name in (role.get("days", []) if role else []):
            if "placed" in unit or attempts >= 24 or state["stop"]:
                break
            day_id = day_name_to_id.get(day_name)
            if day_id is None:
                continue
            for start in (role.get("times", []) if role else []):
                if "placed" in unit or attempts >= 24:
                    break
                try:
                    end = _fmt(time_to_minutes(start) + duration)
                except (ValueError, AttributeError, TypeError):
                    continue
                if (start, end) not in windows:
                    continue
                for teacher_id in teacher_order[:2]:
                    if "placed" in unit:
                        break
                    for room_id in room_order[:2]:
                        if (subject.id, day_id, start) in used_cells:
                            continue
                        if avoid and (subject.id, day_id, start) in avoid:
                            continue
                        attempts += 1
                        cand = {
                            "subject_id": subject.id, "teacher_id": teacher_id,
                            "room_id": room_id, "day_id": day_id,
                            "start_time": start, "end_time": end,
                            "lecture_type": subject.subject_type or "Theory",
                        }
                        try:
                            ok, reason, row = attempt(cand)
                        except Exception:
                            raise
                        if ok:
                            accepted.append(cand)
                            accepted_rows.append(row)
                            push_context(cand)
                            unit["placed"] = cand
                            used_cells.add((subject.id, day_id, start))
                            if len(accepted) > len(best):
                                best = list(accepted)
                            break
                        unit["fail_reason"] = reason
                        if attempts >= 24:
                            break
    # Phase 2: backtracking search for whatever remains.
    deferred = [u for u in units if "placed" not in u]
    if deferred:
        dfs(0, deferred)
    complete = all("placed" in u for u in units)
    # The transaction holds exactly the placed rows; the caller rolls back
    # (dry run) or re-validates + commits. Anything unplaced never touched it.
    final = [u["placed"] for u in units if "placed" in u]
    for unit in units:
        if "placed" in unit:
            continue
        subject = unit["subject"]
        unplaced.append({
            "code": subject.code, "name": subject.name,
            "reason": unit.get("fail_reason", "No valid placement found."),
        })
    return {"accepted": final, "unplaced": unplaced,
            "validations": state["validations"], "complete": complete}
