"""Deterministic weighted scoring. No randomness, no models, no network."""
from typing import Any, Dict, List

from app.utils.helpers import time_to_minutes


def _rank_bonus(order: List[str], value: str, weight: float) -> float:
    if value in order:
        return weight * (1.0 - order.index(value) / len(order))
    return 0.0


def score_candidate(candidate: Dict[str, Any], subject_type: str,
                    patterns: Dict[str, Any], context: Dict[str, Any]) -> float:
    """Score one candidate against patterns + already-placed context.

    context = {"by_day_subject": {day_id: {subject_id: [start,...]}},
               "day_load": {day_id: int}, "teacher_load": {teacher_id: int}}.
    """
    score = 0.0
    score += _rank_bonus(patterns.get("preferred_days", []),
                         context["day_names"].get(candidate["day_id"], ""), 20.0)
    score += _rank_bonus(patterns.get("preferred_times", []),
                         candidate["start_time"], 15.0)
    same_day = context["by_day_subject"].get(candidate["day_id"], {}).get(
        candidate["subject_id"], [])
    if (subject_type or "Theory") != "Theory" and patterns.get("wants_consecutive_practicals"):
        try:
            here = time_to_minutes(candidate["start_time"])
            adjacent = any(
                0 < abs(here - time_to_minutes(t)) <= 70 for t in same_day)
        except (ValueError, AttributeError, TypeError):
            adjacent = False
        score += 20.0 if adjacent else (5.0 if same_day else 10.0)
    else:
        score += 15.0 if not same_day else 0.0
    target = patterns.get("target_daily_load") or 0.0
    load = context["day_load"].get(candidate["day_id"], 0)
    if target > 0:
        score += 15.0 * max(0.0, 1.0 - load / max(target * 1.5, 1.0))
    else:
        score += 15.0 * (1.0 / (1.0 + load))
    teacher_loads = context["teacher_load"]
    if teacher_loads:
        deepest = max(teacher_loads.values())
        score += 10.0 * (1.0 - teacher_loads.get(candidate["teacher_id"], 0) / max(1, deepest + 1))
    else:
        score += 10.0
    morning_share = patterns.get("morning_share", 0.5)
    try:
        is_morning = time_to_minutes(candidate["start_time"]) < 12 * 60
    except (ValueError, AttributeError, TypeError):
        is_morning = True
    if morning_share >= 0.7 and is_morning:
        score += 5.0
    elif morning_share <= 0.3 and not is_morning:
        score += 5.0
    elif 0.3 < morning_share < 0.7:
        score += 2.5
    return round(score, 3)


def score_timetable(placed: List[Dict[str, Any]]) -> float:
    return round(float(len(placed)), 3)
