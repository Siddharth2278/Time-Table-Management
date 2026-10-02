"""TimetableTemplate: the structural SHAPE of a reference timetable.

Roles describe subject shapes by frequency/type/duration — never by name —
so a new semester with different subjects can inherit the same structure.
"""
from typing import Any, Dict, List

from app.models import TimeSlot, WorkingDay
from app.services.intelligence.structural_analyzer import analyze_structure
from app.utils.helpers import time_to_minutes


def _periods_around_breaks(session, semester_id: int, breaks: List[dict]) -> Dict[str, Any]:
    from app.models import TimetableEntry
    entries = session.query(TimetableEntry).filter(
        TimetableEntry.semester_id == semester_id).all()
    before = after = 0
    for e in entries:
        try:
            start = time_to_minutes(e.start_time)
            end = time_to_minutes(e.end_time)
        except (ValueError, AttributeError, TypeError):
            continue
        for b in breaks:
            try:
                bs = time_to_minutes(b["start"])
                be = time_to_minutes(b["end"])
            except (ValueError, AttributeError, TypeError, KeyError):
                continue
            if end <= bs:
                before += 1
            elif start >= be:
                after += 1
    return {"periods_before_break": before, "periods_after_break": after}


def build_template(session, ref_sem_id: int) -> Dict[str, Any]:
    """Build the structural template. Raises IntelligenceError when empty."""
    from app.services.intelligence.timetable_agent import IntelligenceError
    from app.services.intelligence.reference_analyzer import analyze_reference
    profile = analyze_reference(session, ref_sem_id)
    if not profile.get("has_data"):
        raise IntelligenceError(
            "Reference timetable is empty. Pick a semester with lectures.")
    return template_from_profile(session, profile, ref_sem_id)


def template_from_profile(session, profile: Dict[str, Any],
                          ref_sem_id=None) -> Dict[str, Any]:
    """Build the template from any profile (database or external file)."""
    from app.utils.helpers import time_to_minutes as _t2m
    order_names = [d.name for d in session.query(WorkingDay).order_by(
        WorkingDay.sort_order).all()]
    day_order = {name: i for i, name in enumerate(order_names)}
    days = session.query(WorkingDay).filter(
        WorkingDay.is_enabled == True).order_by(WorkingDay.sort_order).all()  # noqa: E712
    total = max(1, profile["total_lectures"])

    def _safe_minutes(t):
        try:
            return _t2m(t)
        except (ValueError, AttributeError, TypeError):
            return -1

    roles = []
    for s in profile.get("subjects", []):
        ordered_days = sorted(s.get("days", []), key=lambda d: day_order.get(d, 999))
        indexes = [day_order.get(d, 999) for d in ordered_days]
        gaps = [b - a for a, b in zip(indexes, indexes[1:])]
        avg_gap = round(sum(gaps) / len(gaps), 2) if gaps else 0.0
        practical = (s.get("type") or "Theory") != "Theory"
        if practical:
            spacing = "grouped"
        elif not gaps:
            spacing = "single-day" if len(ordered_days) <= 1 else "tight"
        elif avg_gap <= 1.5:
            spacing = "tight"
        elif avg_gap <= 2.5:
            spacing = "distributed"
        else:
            spacing = "sparse"
        times = sorted(s.get("times", []))
        try:
            morning = sum(1 for t in times if _t2m(t) < 12 * 60)
        except (ValueError, AttributeError, TypeError):
            morning = 0
        after = len(times) - morning
        period_pref = ("morning" if morning > after else
                       "afternoon" if after > morning else "mixed")
        minute_list = sorted(m for m in (_safe_minutes(t) for t in times) if m >= 0)
        consecutive_block = practical and any(
            0 < b - a <= 70 for a, b in zip(minute_list, minute_list[1:]))
        try:
            duration = int(s.get("duration") or 60)
        except (TypeError, ValueError):
            duration = 60
        roles.append({
            "frequency": s.get("count", 0),
            "day_count": len(ordered_days),
            "days": ordered_days,
            "day_indexes": indexes,
            "gaps": gaps,
            "avg_gap": avg_gap,
            "spacing": spacing,
            "period_pref": period_pref,
            "times": times,
            "practical": practical,
            "consecutive_block": consecutive_block,
            "block_lengths": [],
            "duration": duration,
            "type_class": "practical" if practical else "theory",
        })

    practical_roles = [r for r in roles if r["practical"]]
    day_load = profile.get("day_distribution", {}) or {}
    day_shares = {d: day_load.get(d, 0) / total for d in [x.name for x in days]}
    time_load: Dict[str, int] = dict(profile.get("time_distribution", {}) or {})
    time_shares = {t: time_load[t] / total for t in time_load}
    return {
        "reference_semester_id": ref_sem_id,
        "reference_name": profile.get("semester", {}).get("name", ""),
        "total_lectures": profile["total_lectures"],
        "roles": roles,
        "day_load_profile": day_shares,
        "time_load_profile": time_shares,
        "break_positions": _periods_around_breaks(session, ref_sem_id, profile.get("breaks", [])),
        "breaks": profile.get("breaks", []),
        "daily_density": profile.get("density", 0.0),
        "morning_share": (profile.get("morning_lectures", 0) / total),
        "free_periods": profile.get("free_periods", 0),
        "teacher_load_profile": profile.get("teacher_load", {}),
        "room_load_profile": profile.get("room_load", {}),
        "practical_block_patterns": [{
            "duration": r["duration"], "period": r["period_pref"],
            "block_lengths": r["block_lengths"],
        } for r in practical_roles],
        "first_last": profile.get("first_last", {}),
        "working_days": [d.name for d in days],
    }
