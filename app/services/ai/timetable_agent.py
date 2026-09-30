"""AI timetable agent: online generation with offline-grade safety.

- Internet is verified before anything else; offline disables the flow.
- The model proposes; ConflictService disposes. Every entry is validated
  with the existing engine (teacher / semester / room / availability /
  break / subject limit) plus an explicit room-type check.
- Dry runs happen inside a rolled-back transaction: Cancel (or any
  failure) leaves the database byte-identical.
- Apply is all-or-nothing: validate everything first, then insert and
  commit once; any failure rolls everything back.
"""
from typing import Any, Callable, Dict, List, Optional

from app.models import Room, Subject
from app.services.ai.ai_client import (
    AIConfig, AIError, post_chat, provider_status,
)
from app.services.ai.prompt_builder import (
    build_messages, build_payload, build_reference_profile,
)
from app.services.ai.timetable_parser import parse_proposal
from app.services.conflict_service import ConflictService
from app.services.timetable_service import TimetableService

STAGES = ["internet", "reference", "requirements", "teachers",
          "rooms", "breaks", "generated", "validated"]


def _room_type_ok(session, subject_id: int, room_id: int) -> Optional[str]:
    subject = session.query(Subject).filter(Subject.id == subject_id).first()
    room = session.query(Room).filter(Room.id == room_id).first()
    if subject is None or room is None:
        return "Unknown subject or room."
    need = (subject.room_requirement or "").strip().lower()
    if need and need != (room.type or "").strip().lower():
        return f"Room type mismatch: {subject.code} needs {subject.room_requirement}."
    return None


def _validate_batch(session, semester_id: int, entries: List[dict]):
    """Validate entries in order against live + already-accepted batch state.

    Uses the session's own transaction (flushed, never committed) so batch
    self-conflicts are caught exactly like manual entry. Returns
    (accepted, rejected) where rejected items carry real engine reasons.
    """
    accepted: List[dict] = []
    rejected: List[dict] = []
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
            accepted.append(entry)
        except Exception as e:
            session.rollback()
            raise AIError(f"Database failure during validation: {e}", kind="db")
    return accepted, rejected


def _to_row(semester_id: int, entry: dict):
    from app.models import TimetableEntry
    return TimetableEntry(
        semester_id=semester_id, subject_id=entry["subject_id"],
        teacher_id=entry["teacher_id"], room_id=entry["room_id"],
        day_id=entry["day_id"], start_time=entry["start_time"],
        end_time=entry["end_time"],
        lecture_type=entry.get("lecture_type") or "Theory")


def _known_ids(session, semester_id: int) -> dict:
    from app.models import Room as _R, Teacher as _T, WorkingDay as _D, Subject as _S
    return {
        "subjects": {s.id for s in session.query(_S).filter(
            _S.semester_id == semester_id).all()},
        "teachers": {t.id for t in session.query(_T).all()},
        "rooms": {r.id for r in session.query(_R).all()},
        "days": {d.id for d in session.query(_D).all()},
    }


def _diff(existing: List[dict], proposed: List[dict]) -> dict:
    key = lambda e: (e["day_id"], e["start_time"], e["end_time"],
                     e["subject_id"], e["teacher_id"], e["room_id"])
    old, new = {key(e) for e in existing}, {key(e) for e in proposed}
    return {"existing": len(old), "generated": len(new),
            "unchanged": len(old & new), "changed": len(new - old)}


def _explain(session, target_sem_id: int, ref_profile: dict,
             accepted: List[dict], rejected: List[dict]) -> str:
    counts: Dict[str, int] = {}
    for e in accepted:
        sub = session.query(Subject).filter(Subject.id == e["subject_id"]).first()
        label = f"{sub.code}: {sub.name}" if sub else f"Subject {e['subject_id']}"
        counts[label] = counts.get(label, 0) + 1
    days = sorted({e["day_id"] for e in accepted})
    lines = [f"Generated using {ref_profile.get('semester', {}).get('name', 'reference')} as reference."]
    lines += [f"{label}: {n}/week" for label, n in sorted(counts.items())]
    lines.append(f"Teaching days used: {len(days)}.")
    lines.append(f"{len(rejected)} placement(s) rejected by conflict validation.")
    lines.append("0 conflicts in the accepted proposal.")
    return "\n".join(lines)


def run(session, target_sem_id: int, ref_sem_id: int, mode: str,
        config: AIConfig, progress: Optional[Callable[[str], None]] = None,
        _retries: int = 1) -> Dict[str, Any]:
    """Full pipeline. Returns proposal; writes NOTHING (rolled-back dry run)."""
    done = progress or (lambda stage: None)

    status = provider_status(config)
    if status["state"] != "ready":
        raise AIError(status["message"],
                      kind="offline" if status["state"] == "offline" else "config")
    done("internet")

    ref_profile = build_reference_profile(session, ref_sem_id)
    if not ref_profile.get("has_data"):
        raise AIError("Reference timetable is empty. Pick a semester with lectures.",
                      kind="data")
    done("reference")

    payload = build_payload(session, target_sem_id, ref_sem_id, mode)
    if not payload["subjects"]:
        raise AIError("Target semester has no subjects.", kind="data")
    done("requirements")
    if not payload["teachers"]:
        raise AIError("No active teachers.", kind="data")
    done("teachers")
    if not payload["rooms"]:
        raise AIError("No available rooms.", kind="data")
    done("rooms")
    done("breaks")

    messages = build_messages(payload)
    response = post_chat(config, messages)
    proposal = parse_proposal(response, target_sem_id,
                              _known_ids(session, target_sem_id))
    done("generated")

    if mode == "replace":
        prior = session.query(_entry_model()).filter(
            _entry_model().semester_id == target_sem_id).all()
        for row in prior:
            session.delete(row)
        session.flush()
    try:
        accepted, rejected = _validate_batch(session, target_sem_id, proposal["entries"])
    finally:
        session.rollback()
    done("validated")

    if (rejected or proposal.get("dropped")) and _retries > 0:
        return _retry(session, target_sem_id, ref_sem_id, mode, config,
                      payload, proposal, rejected, done)
    return _finish(session, target_sem_id, ref_profile, payload,
                   accepted, rejected, proposal)


def _retry(session, target_sem_id, ref_sem_id, mode, config, payload,
           proposal, rejected, done):
    notes = [str(r) for r in rejected[:10]] + [str(d) for d in proposal.get("dropped", [])[:10]]
    fix_messages = build_messages(payload) + [{
        "role": "user",
        "content": ("Your previous proposal had these problems; return a corrected "
                    "full proposal in the same strict JSON schema:\n" + "\n".join(notes)),
    }]
    try:
        response = post_chat(config, fix_messages)
        proposal = parse_proposal(response, target_sem_id,
                                  _known_ids(session, target_sem_id))
    except AIError:
        pass
    if mode == "replace":
        for row in session.query(_entry_model()).filter(
                _entry_model().semester_id == target_sem_id).all():
            session.delete(row)
        session.flush()
    try:
        accepted, rejected = _validate_batch(session, target_sem_id, proposal["entries"])
    finally:
        session.rollback()
    done("validated")
    ref_profile = payload["reference_profile"]
    return _finish(session, target_sem_id, ref_profile, payload,
                   accepted, rejected, proposal)


def _finish(session, target_sem_id, ref_profile, payload, accepted,
            rejected, proposal):
    existing = payload["fixed_entries"]
    return {
        "mode": payload["mode"],
        "reference": ref_profile,
        "accepted": accepted,
        "rejected": rejected,
        "model_unplaced": proposal.get("unplaced", []),
        "explanation": _explain(session, target_sem_id, ref_profile,
                                accepted, rejected)
        + (f"\n\nModel notes: {proposal.get('explanation', '')}"
           if proposal.get("explanation") else ""),
        "diff": _diff(existing, accepted),
    }


def _entry_model():
    from app.models import TimetableEntry
    return TimetableEntry


def apply_proposal(session, target_sem_id: int, proposal: Dict[str, Any],
                   mode: str) -> Dict[str, int]:
    """All-or-nothing apply. Validates everything first; rollback on failure."""
    entries = list(proposal.get("accepted", []))
    try:
        if mode == "replace":
            for row in session.query(_entry_model()).filter(
                    _entry_model().semester_id == target_sem_id).all():
                session.delete(row)
            session.flush()
        accepted, rejected = _validate_batch(session, target_sem_id, entries)
        if rejected or len(accepted) != len(entries):
            session.rollback()
            return {"applied": 0, "rejected": len(rejected)}
        session.commit()
        return {"applied": len(accepted), "rejected": 0}
    except Exception:
        session.rollback()
        raise
