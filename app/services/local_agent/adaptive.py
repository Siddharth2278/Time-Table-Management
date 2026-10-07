"""Adaptive learning: validated feedback + threshold-gated retraining.

Feedback rows are plain lecture dicts (same shape as training rows) with an
extra ``source`` tag (``manual-edit``, ``accepted-schedule``, ``import``).
Only structurally valid rows are stored; conflict/availability validation
happens against the live DB before recording (see ``record_feedback``).

Retraining is threshold-gated and never per-click: ``maybe_retrain`` retrains
only when ``pending >= min_examples``. UI shows pending count, model version,
last training time/rows and whether retraining is pending.
"""
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.services.local_agent.model_versions import feedback_dir, snapshot_version
from app.services.local_agent.schemas import LearningError

FEEDBACK_FILENAME = "feedback.jsonl"
DEFAULT_MIN_EXAMPLES = 20


def _feedback_path(data_dir: Optional[Path] = None) -> Path:
    return feedback_dir(data_dir) / FEEDBACK_FILENAME


def _validate_row(raw: Dict[str, Any]) -> Dict[str, Any]:
    row = dict(raw)
    for key in ("code", "day", "start", "end"):
        if not str(row.get(key, "")).strip():
            raise LearningError(f"Feedback row is missing '{key}'.")
    try:
        duration = int(row.get("duration", 60) or 60)
    except (TypeError, ValueError):
        raise LearningError("Feedback row has an invalid duration.")
    if duration <= 0:
        raise LearningError("Feedback row has an invalid duration.")
    row["duration"] = duration
    from app.utils.helpers import time_to_minutes
    try:
        start, end = time_to_minutes(str(row.get("start", ""))), time_to_minutes(
            str(row.get("end", "")))
    except (TypeError, ValueError, AttributeError):
        raise LearningError("Feedback row has unreadable start/end times.")
    if end <= start:
        raise LearningError("Feedback row end time must be after start time.")
    row.setdefault("type", "Theory")
    row.setdefault("source", "manual-edit")
    return row


def record_feedback(rows: List[Dict[str, Any]],
                    data_dir: Optional[Path] = None,
                    session=None) -> int:
    """Validate + append feedback rows. Returns number recorded."""
    if not rows:
        raise LearningError("No feedback rows supplied.")
    clean = [_validate_row(r) for r in rows]
    if session is not None:
        # Hard-gate: only conflict-free, availability-respecting placements
        # may influence future training.
        from app.models import Room, Subject, Teacher, WorkingDay
        from app.services.conflict_service import ConflictService
        for row in clean:
            subject = session.query(Subject).filter(
                Subject.code == str(row.get("code", "")).strip()).first()
            teacher = session.query(Teacher).filter(
                Teacher.name == str(row.get("teacher", "")).strip()).first()
            room = session.query(Room).filter(
                Room.name == str(row.get("room", "")).strip()).first()
            day = session.query(WorkingDay).filter(
                WorkingDay.name == str(row.get("day", "")).strip()).first()
            if subject is None or teacher is None or room is None or day is None:
                raise LearningError(
                    "Feedback references an unknown subject, teacher, "
                    "room or day; only valid accepted schedules count.")
            problems = [c for c in ConflictService.validate_all(
                session, subject.semester_id, subject.id, teacher.id,
                room.id, day.id, str(row["start"]), str(row["end"]),
                exclude_id=None, check_subject_limit=False) if c.has_conflict]
            if problems:
                raise LearningError(
                    f"Feedback placement conflicts: {problems[0].message}. "
                    "Only valid accepted schedules may influence training.")
    path = _feedback_path(data_dir)
    with open(path, "a", encoding="utf-8") as fh:
        for row in clean:
            fh.write(json.dumps(row) + "\n")
    return len(clean)


def pending_feedback(data_dir: Optional[Path] = None) -> List[Dict[str, Any]]:
    path = _feedback_path(data_dir)
    rows = []
    if path.is_file():
        try:
            with open(path, "r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if line:
                        rows.append(json.loads(line))
        except (OSError, ValueError) as e:
            raise LearningError(f"Feedback log is unreadable: {e}")
    return rows


def clear_feedback(data_dir: Optional[Path] = None) -> int:
    path = _feedback_path(data_dir)
    try:
        count = len(pending_feedback(data_dir))
    except LearningError:
        count = 0
    try:
        if path.exists():
            path.unlink()
    except OSError as e:
        raise LearningError(f"Cannot clear feedback: {e}")
    return count


# ---- settings (stored in the existing Setting table) ----

_DEFAULTS = {
    "adaptive_enabled": "1",
    "adaptive_min_examples": str(DEFAULT_MIN_EXAMPLES),
    "adaptive_background": "0",
    "ai_data_mode": "local",
}


def get_setting(key: str) -> str:
    from app.database import get_session
    from app.models import Setting
    session = get_session()
    try:
        row = session.query(Setting).filter(Setting.key == key).first()
        if row is not None and row.value not in (None, ""):
            return str(row.value)
    finally:
        try:
            session.close()
        except Exception:
            pass
    return _DEFAULTS.get(key, "")


def set_setting(key: str, value: str) -> None:
    from app.database import get_session
    from app.models import Setting
    session = get_session()
    try:
        row = session.query(Setting).filter(Setting.key == key).first()
        if row is None:
            session.add(Setting(key=key, value=str(value)))
        else:
            row.value = str(value)
        session.commit()
    except Exception as e:
        try:
            session.rollback()
        except Exception:
            pass
        raise LearningError(f"Cannot save setting '{key}': {e}")
    finally:
        try:
            session.close()
        except Exception:
            pass


def adaptive_config() -> Dict[str, Any]:
    try:
        min_examples = int(get_setting("adaptive_min_examples") or DEFAULT_MIN_EXAMPLES)
    except (TypeError, ValueError):
        min_examples = DEFAULT_MIN_EXAMPLES
    return {
        "enabled": (get_setting("adaptive_enabled") or "1") == "1",
        "min_examples": max(1, min_examples),
        "background": (get_setting("adaptive_background") or "0") == "1",
        "ai_data_mode": get_setting("ai_data_mode") or "local",
    }


def adaptive_status(data_dir: Optional[Path] = None) -> Dict[str, Any]:
    """UI-facing status: pending count, model version/time/rows, retrain flag."""
    from app.services.local_agent import model_store
    try:
        pending = len(pending_feedback(data_dir))
    except LearningError:
        pending = 0
    try:
        status = model_store.model_status(data_dir)
    except Exception:
        status = {"trained": False}
    config = adaptive_config()
    return {
        "enabled": config["enabled"],
        "min_examples": config["min_examples"],
        "background": config["background"],
        "pending": pending,
        "trained": bool(status.get("trained")),
        "model_version": status.get("model_version"),
        "trained_at": status.get("trained_at", ""),
        "lectures": status.get("lectures", status.get("stored_rows", 0)),
        "retrain_pending": bool(config["enabled"] and pending >= config["min_examples"]),
    }


def maybe_retrain(data_dir: Optional[Path] = None,
                  force: bool = False) -> Optional[Dict[str, Any]]:
    """Retrain when pending feedback reaches the threshold (or force=True).

    Snapshots the previous model first; clears feedback only on success.
    Returns the training report, or None when below threshold.
    """
    from app.services.local_agent import model_store
    from app.services.local_agent.agent import TimetableAgent
    config = adaptive_config()
    if not config["enabled"] and not force:
        return None
    pending = pending_feedback(data_dir)
    if not force and len(pending) < config["min_examples"]:
        return None
    if not pending:
        raise LearningError("No feedback collected yet.")
    snapshot_version(data_dir, label="pre-adaptive")
    agent = TimetableAgent(data_dir=data_dir)
    snap = agent._snapshot_store()
    try:
        report = model_store.train_from_rows(
            pending, source_label="adaptive-feedback",
            data_dir=agent._data_dir, replace=False)
    except Exception:
        raise
    report["files"] = ["adaptive-feedback"]
    try:
        agent._verify_persisted_model(report)
        agent._rebuild_profile_from_dataset()
    except Exception:
        agent._restore_snapshot(snap)
        raise
    clear_feedback(data_dir)
    report["feedback_consumed"] = len(pending)
    return report


def training_history(data_dir: Optional[Path] = None, limit: int = 20) -> Dict[str, Any]:
    """Versions + recent feedback sources for the Training History view."""
    from app.services.local_agent import model_versions
    versions = model_versions.sorted_versions(data_dir)[-limit:]
    try:
        feedback = pending_feedback(data_dir)[-limit:]
    except LearningError:
        feedback = []
    return {"versions": versions, "pending_feedback": feedback,
            "status": adaptive_status(data_dir)}
