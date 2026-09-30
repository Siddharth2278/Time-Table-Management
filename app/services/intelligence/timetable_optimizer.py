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

from app.models import Room, Subject
from app.services.conflict_service import ConflictService
from app.services.intelligence.candidate_generator import generate_candidates
from app.services.intelligence.timetable_scorer import score_candidate

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
             budget: int = DEFAULT_BUDGET) -> Dict[str, Any]:
    """Place lecture units. Returns {accepted, unplaced, validations, complete}."""
    context = _empty_context()
    context["day_names"] = day_names
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

    def dfs(index: int) -> bool:
        nonlocal best
        if state["stop"] or index >= len(units):
            return True
        unit = units[index]
        candidates = generate_candidates(session, unit["subject"], patterns)
        scored = sorted(
            ((score_candidate(c, unit["subject"].subject_type, patterns, context),
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
                if len(accepted) > len(best):
                    best = list(accepted)
                if dfs(index + 1):
                    return True
                accepted.pop()
                accepted_rows.pop()
                rebuild_context()
                undo(row)
            else:
                last_reason = reason
        unit["fail_reason"] = last_reason
        return False

    complete = dfs(0)
    # Leave the transaction holding exactly the best prefix found; the
    # caller rolls everything back (dry run) or re-validates + commits.
    # Anything beyond the best prefix never touched the database.
    final = best if not complete else accepted
    for pos, unit in enumerate(units):
        if pos < len(final):
            continue
        subject = unit["subject"]
        if pos == len(final):
            reason = unit.get("fail_reason", "No valid placement found.")
        else:
            reason = "Not attempted: an earlier lecture could not be placed."
        unplaced.append({
            "code": subject.code, "name": subject.name, "reason": reason,
        })
    return {"accepted": final, "unplaced": unplaced,
            "validations": state["validations"], "complete": complete}
