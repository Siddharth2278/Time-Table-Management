"""Local-only profile storage. No upload, telemetry, cloud or external DB.

The profile lives as versioned JSON in the application's own data
directory (the same per-user folder as timetable.db), so each
installation owns exactly its own learned profile.
"""
import json
from pathlib import Path
from typing import Any, Dict, Optional

from app.database import get_data_dir
from app.services.local_agent.schemas import (
    PROFILE_FILENAME, PROFILE_VERSION, LearningError,
)


def profile_path(data_dir: Optional[Path] = None) -> Path:
    base = Path(data_dir) if data_dir is not None else get_data_dir()
    base.mkdir(parents=True, exist_ok=True)
    return base / PROFILE_FILENAME


def save_profile(profile: Dict[str, Any], data_dir: Optional[Path] = None) -> Path:
    """Persist a learned profile locally (overwrite)."""
    if not isinstance(profile, dict) or profile.get("version") != PROFILE_VERSION:
        raise LearningError("Refusing to save an invalid learning profile.")
    path = profile_path(data_dir)
    try:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(profile, fh, indent=1)
    except OSError as e:
        raise LearningError(f"Cannot save learning profile to '{path}': {e}")
    return path


def load_profile(data_dir: Optional[Path] = None) -> Dict[str, Any]:
    """Load the local profile. Errors when none learned yet or unreadable."""
    path = profile_path(data_dir)
    if not path.exists():
        raise LearningError(
            "No learned profile yet. Analyze a reference timetable first.")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            profile = json.load(fh)
    except (OSError, ValueError) as e:
        raise LearningError(f"Cannot read learning profile '{path}': {e}")
    if not isinstance(profile, dict) or profile.get("version") != PROFILE_VERSION:
        raise LearningError(
            f"Learning profile '{path}' has an unsupported version. "
            "Clear it and analyze a reference timetable again.")
    return profile


def update_profile(new_profile: Dict[str, Any],
                   data_dir: Optional[Path] = None) -> Dict[str, Any]:
    """Merge a freshly learned profile into the stored one (weighted).

    Totals and load counters add up; shares and role aggregates are
    recomputed; subject facts union by code; source files accumulate.
    Used for incremental learning from additional timetable files.
    """
    if not isinstance(new_profile, dict) or new_profile.get("version") != PROFILE_VERSION:
        raise LearningError("Refusing to merge an invalid learning profile.")
    try:
        current = load_profile(data_dir)
    except LearningError:
        return _with_saved(save_profile(new_profile, data_dir), new_profile)

    merged_sources = list(dict.fromkeys(
        current.get("sources", []) + new_profile.get("sources", [])))
    old_total = int(current.get("total_lectures", 0))
    new_total = int(new_profile.get("total_lectures", 0))
    total = old_total + new_total

    subjects: Dict[str, dict] = {s["code"]: dict(s) for s in current.get("subjects", [])}
    for s in new_profile.get("subjects", []):
        if s["code"] in subjects:
            old = subjects[s["code"]]
            old["count"] = old.get("count", 0) + s.get("count", 0)
            old["days"] = sorted(set(old.get("days", [])) | set(s.get("days", [])))
            old["times"] = sorted(set(old.get("times", [])) | set(s.get("times", [])))
            old["morning"] = old.get("morning", 0) + s.get("morning", 0)
            old["afternoon"] = old.get("afternoon", 0) + s.get("afternoon", 0)
        else:
            subjects[s["code"]] = dict(s)

    def _add_counters(*maps):
        merged: Dict[str, int] = {}
        for mapping in maps:
            for key, value in (mapping or {}).items():
                merged[key] = merged.get(key, 0) + int(value or 0)
        return merged

    roles: Dict[str, dict] = {}
    for key in set(current.get("roles", {})) | set(new_profile.get("roles", {})):
        old = current.get("roles", {}).get(key, {})
        new = new_profile.get("roles", {}).get(key, {})
        old_n = old.get("subjects_observed", 0)
        new_n = new.get("subjects_observed", 0)
        denom = max(1, old_n + new_n)
        merged_gaps = sorted((old.get("gaps", []) or []) + (new.get("gaps", []) or []))[:64]
        roles[key] = {
            "type": new.get("type", old.get("type", "theory")),
            "duration": new.get("duration", old.get("duration", 60)),
            "frequency": new.get("frequency", old.get("frequency", 0)),
            "subjects_observed": old_n + new_n,
            "avg_day_count": round(
                (old.get("avg_day_count", 0) * old_n
                 + new.get("avg_day_count", 0) * new_n) / denom, 2),
            "preferred_days": _merge_ranked(old.get("preferred_days", []),
                                            new.get("preferred_days", [])),
            "preferred_times": _merge_ranked(old.get("preferred_times", []),
                                             new.get("preferred_times", [])),
            "morning_share": round(
                (old.get("morning_share", 0) * old_n
                 + new.get("morning_share", 0) * new_n) / denom, 3),
            "adjacent_pair_rate": round(
                (old.get("adjacent_pair_rate", 0) * old_n
                 + new.get("adjacent_pair_rate", 0) * new_n) / denom, 3),
            "avg_gap": round(sum(merged_gaps) / len(merged_gaps), 2) if merged_gaps else 0.0,
            "gaps": merged_gaps,
            "day_counts": _add_counters(old.get("day_counts"), new.get("day_counts")),
            "time_counts": _add_counters(old.get("time_counts"), new.get("time_counts")),
        }

    old_patterns = current.get("patterns", {})
    new_patterns = new_profile.get("patterns", {})
    day_load = _add_counters(old_patterns.get("daily_load"), new_patterns.get("daily_load"))
    time_load = _add_counters(old_patterns.get("time_load"), new_patterns.get("time_load"))
    teacher_load = _add_counters(old_patterns.get("teacher_workload"),
                                 new_patterns.get("teacher_workload"))
    room_load = _add_counters(old_patterns.get("room_usage"), new_patterns.get("room_usage"))

    def _ranked(counter):
        from collections import Counter as _Counter
        ranked = _Counter(counter).most_common()
        ranked.sort(key=lambda kv: (-kv[1], kv[0]))
        return [k for k, _ in ranked]

    merged = {
        "version": PROFILE_VERSION,
        "sources": merged_sources,
        "total_lectures": total,
        "subjects": [subjects[k] for k in sorted(subjects)],
        "roles": roles,
        "patterns": {
            "preferred_days": _ranked(day_load),
            "preferred_times": _ranked(time_load),
            "morning_share": round(
                (old_patterns.get("morning_share", 0) * old_total
                 + new_patterns.get("morning_share", 0) * new_total) / max(1, total), 3),
            "average_daily_load": round(total / max(1, len(day_load)), 2),
            "min_daily_load": min(day_load.values()) if day_load else 0,
            "max_daily_load": max(day_load.values()) if day_load else 0,
            "daily_load": dict(sorted(day_load.items())),
            "time_load": dict(sorted(time_load.items())),
            "teacher_workload": dict(sorted(teacher_load.items())),
            "teacher_min": min(teacher_load.values()) if teacher_load else 0,
            "teacher_max": max(teacher_load.values()) if teacher_load else 0,
            "teacher_avg": round(sum(teacher_load.values()) / max(1, len(teacher_load)), 2),
            "room_usage": dict(sorted(room_load.items())),
            "room_min": min(room_load.values()) if room_load else 0,
            "room_max": max(room_load.values()) if room_load else 0,
            "theory_duration": new_patterns.get("theory_duration",
                                                old_patterns.get("theory_duration")),
            "practical_duration": new_patterns.get("practical_duration",
                                                   old_patterns.get("practical_duration")),
        },
    }
    save_profile(merged, data_dir)
    return merged


def _with_saved(path: Path, profile: Dict[str, Any]) -> Dict[str, Any]:
    profile["saved_to"] = str(path)
    return profile


def _merge_ranked(old: list, new: list) -> list:
    seen = list(dict.fromkeys(list(old or []) + list(new or [])))
    return seen


def clear_profile(data_dir: Optional[Path] = None) -> bool:
    """Delete the local profile. Returns True when something was removed."""
    path = profile_path(data_dir)
    try:
        if path.exists():
            path.unlink()
            return True
        return False
    except OSError as e:
        raise LearningError(f"Cannot clear learning profile '{path}': {e}")
