"""Structural similarity scoring: deterministic and explainable.

Candidate score (0-100) blends role fit (day count, spacing,
consecutive behavior, time of day, practical grouping) with template
fit (day/time load shape, balance). Timetable-level similarity reports
the nine §10 components, each 0..1, plus their mean total.
"""
from collections import Counter
from typing import Any, Dict, List

from app.utils.helpers import time_to_minutes


def _jaccard_multiset(left: list, right: list) -> float:
    if not left and not right:
        return 1.0
    if not left or not right:
        return 0.0
    counter_l, counter_r = Counter(left), Counter(right)
    inter = sum((counter_l & counter_r).values())
    union = sum((counter_l | counter_r).values())
    return inter / union if union else 0.0


def _day_gaps(day_ids: list, order: Dict[int, int]) -> list:
    idx = sorted(order.get(d, 10 ** 6) for d in set(day_ids))
    return [b - a for a, b in zip(idx, idx[1:])]


def score_breakdown(candidate: Dict[str, Any], role: dict, template: dict,
                    context: Dict[str, Any]) -> Dict[str, float]:
    """Named 0..1 components for one candidate. Pure arithmetic."""
    order = context.get("day_order", {})
    names = context.get("day_names", {})
    placed = context.get("by_day_subject", {}).get(candidate["day_id"], {}).get(
        candidate["subject_id"], [])
    day_ids = [d for d, subs in context.get("by_day_subject", {}).items()
               if candidate["subject_id"] in subs]
    trial_days = day_ids + ([] if candidate["day_id"] in day_ids else [candidate["day_id"]])

    role_days = role.get("days", []) if role else []
    role_gaps = role.get("gaps", []) if role else []
    role_count = role.get("day_count", 0) if role else 0

    day_count_fit = (min(len(trial_days), role_count) / max(len(trial_days), role_count)
                     if role_count and trial_days else (1.0 if not role_count else 0.0))
    spacing_fit = _jaccard_multiset(role_gaps, _day_gaps(trial_days, order)) if role else 0.5

    role_wants_adjacent = bool(role and (role.get("consecutive_block") or role.get("spacing") in ("tight",)))
    role_avoids = bool(role and role.get("spacing") == "distributed" and not role.get("consecutive_block"))
    try:
        here = time_to_minutes(candidate["start_time"])
        adjacent = any(
            0 < abs(here - time_to_minutes(t)) <= 70
            for d, subs in context.get("by_day_subject", {}).items()
            for t in subs.get(candidate["subject_id"], []))
    except (ValueError, AttributeError, TypeError):
        adjacent = False
    if role_wants_adjacent:
        consecutive_fit = 1.0 if (adjacent or not placed) else 0.4
    elif role_avoids and adjacent:
        consecutive_fit = 0.0
    else:
        consecutive_fit = 0.7

    period = (role or {}).get("period_pref", "mixed")
    try:
        is_morning = time_to_minutes(candidate["start_time"]) < 12 * 60
    except (ValueError, AttributeError, TypeError):
        is_morning = True
    if period == "mixed":
        time_of_day_fit = 0.7
    else:
        time_of_day_fit = 1.0 if (period == "morning") == is_morning else 0.2

    day_shares = template.get("day_load_profile", {}) if template else {}
    day_dist_fit = day_shares.get(names.get(candidate["day_id"], ""), 0.0)
    time_shares = template.get("time_load_profile", {}) if template else {}
    time_dist_fit = time_shares.get(candidate["start_time"], 0.0)

    practical = bool(role and role.get("practical"))
    if practical:
        practical_fit = 1.0 if (adjacent or not placed) else 0.3
    else:
        practical_fit = 1.0 if not placed else 0.4

    target_share = day_shares.get(names.get(candidate["day_id"], ""), 0.0)
    placed_total = max(1, sum(context.get("day_load", {}).values()))
    placed_share = context.get("day_load", {}).get(candidate["day_id"], 0) / placed_total
    load_balance = max(0.0, min(1.0, 1.0 - (placed_share - target_share) * 4))
    teacher_loads = context.get("teacher_load", {})
    if teacher_loads:
        deepest = max(teacher_loads.values())
        teacher_balance = 1.0 - teacher_loads.get(candidate["teacher_id"], 0) / max(1, deepest + 1)
    else:
        teacher_balance = 1.0
    return {
        "day_count": round(day_count_fit, 3),
        "spacing": round(spacing_fit, 3),
        "consecutive": round(consecutive_fit, 3),
        "time_of_day": round(time_of_day_fit, 3),
        "day_dist": round(day_dist_fit, 3),
        "time_dist": round(time_dist_fit, 3),
        "practical": round(practical_fit, 3),
        "load_balance": round(load_balance, 3),
        "teacher_balance": round(teacher_balance, 3),
    }


_WEIGHTS = {
    "day_count": 12.0, "spacing": 18.0, "consecutive": 10.0,
    "time_of_day": 10.0, "day_dist": 12.0, "time_dist": 10.0,
    "practical": 12.0, "load_balance": 10.0, "teacher_balance": 6.0,
}

PLAN_BONUS_TOP = 15.0
PLAN_BONUS_STEP = 3.0


def plan_bonus_for(candidate: Dict[str, Any], plan: Dict[tuple, int] | None,
                   day_names: Dict[int, str]) -> float:
    """Local-model guidance as a bounded bonus (validity never scores).

    plan maps (subject_id, day_name, start_time) -> preference rank (1 = best).
    Unknown cells get zero. Pure addition on top of structural scoring.
    """
    if not plan:
        return 0.0
    rank = plan.get((candidate["subject_id"],
                     day_names.get(candidate["day_id"], ""),
                     candidate["start_time"]))
    if rank is None:
        return 0.0
    try:
        rank = int(rank)
    except (TypeError, ValueError):
        return 0.0
    if rank < 1:
        return 0.0
    return round(max(0.0, PLAN_BONUS_TOP - PLAN_BONUS_STEP * (rank - 1)), 3)


def score_candidate(candidate: Dict[str, Any], subject, role: dict,
                    template: dict, context: Dict[str, Any],
                    plan: Dict[tuple, int] | None = None) -> float:
    """Weighted 0-100 structural score for one candidate, plus plan bonus."""
    parts = score_breakdown(candidate, role or {}, template or {}, context)
    base = sum(parts[k] * _WEIGHTS[k] for k in _WEIGHTS)
    return round(base + plan_bonus_for(candidate, plan, context.get("day_names", {})), 3)


def timetable_similarity(placed: List[dict], template: dict,
                         roles: Dict[int, dict],
                         day_names: Dict[int, str]) -> Dict[str, Any]:
    """Nine §10 components (0..1) plus mean total. Fully deterministic."""
    by_subject: Dict[int, list] = {}
    for e in placed:
        by_subject.setdefault(e["subject_id"], []).append(e)
    order = {name: i for i, name in enumerate(template.get("working_days", []))}

    freq, day_count, spacing = [], [], []
    for sid, rows in by_subject.items():
        role = roles.get(sid, {}) or {}
        required = role.get("required", len(rows)) or len(rows) or 1
        freq.append(min(1.0, len(rows) / max(1, required)))
        distinct = {r["day_id"] for r in rows}
        want = role.get("day_count", 0) or len(distinct) or 1
        day_count.append(min(len(distinct), want) / max(len(distinct), want))
        gaps = _day_gaps([r["day_id"] for r in rows],
                         {d: order.get(day_names.get(d, ""), 10 ** 6) for d in distinct})
        spacing.append(_jaccard_multiset(role.get("gaps", []) or [], gaps))

    def _shares(rows, key):
        counts: Dict[str, int] = {}
        for r in rows:
            counts[r[key]] = counts.get(r[key], 0) + 1
        total = max(1, len(rows))
        return {k: v / total for k, v in counts.items()}

    def _l1_similarity(ref, got):
        keys = set(ref) | set(got)
        if not keys:
            return 1.0
        return max(0.0, 1.0 - sum(abs(ref.get(k, 0.0) - got.get(k, 0.0)) for k in keys) / 2.0)

    placed_days = _shares(placed, "day_id")
    ref_days = template.get("day_load_profile", {}) or {}
    ref_days_by_id = {d: ref_days.get(day_names.get(d, ""), 0.0) for d in placed_days}
    day_dist = _l1_similarity(ref_days_by_id, placed_days)
    placed_times = _shares([{"t": e["start_time"]} for e in placed], "t")
    time_dist = _l1_similarity(template.get("time_load_profile", {}) or {}, placed_times)

    practical_roles = [sid for sid, r in roles.items() if (r or {}).get("practical")]
    practical_hits = 0
    for sid in practical_roles:
        rows = by_subject.get(sid, [])
        per_day: Dict[int, list] = {}
        for r in rows:
            per_day.setdefault(r["day_id"], []).append(r["start_time"])
        found = False
        for times in per_day.values():
            if len(times) < 2:
                continue
            try:
                ordered = sorted(time_to_minutes(t) for t in times)
            except (ValueError, AttributeError, TypeError):
                continue
            if any(0 < b - a <= 70 for a, b in zip(ordered, ordered[1:])):
                found = True
        practical_hits += 1 if found or not rows else 0
    practical = (practical_hits / len(practical_roles)) if practical_roles else 1.0

    breaks = template.get("breaks", []) or []
    bad = 0
    for e in placed:
        try:
            smin, emins = time_to_minutes(e["start_time"]), time_to_minutes(e["end_time"])
        except (ValueError, AttributeError, TypeError):
            bad += 1
            continue
        for b in breaks:
            try:
                bs, be = time_to_minutes(b["start"]), time_to_minutes(b["end"])
            except (ValueError, AttributeError, TypeError, KeyError):
                continue
            if smin < be and emins > bs:
                bad += 1
                break
    break_sim = 1.0 if not placed else max(0.0, 1.0 - bad / len(placed))

    day_totals: Dict[int, int] = {}
    for e in placed:
        day_totals[e["day_id"]] = day_totals.get(e["day_id"], 0) + 1
    placed_load = {day_names.get(d, ""): v / max(1, len(placed)) for d, v in day_totals.items()}
    daily_load = _l1_similarity(
        {k: v for k, v in ref_days.items() if k in placed_load}, placed_load)

    morning = afternoon = 0
    for e in placed:
        try:
            if time_to_minutes(e["start_time"]) < 12 * 60:
                morning += 1
            else:
                afternoon += 1
        except (ValueError, AttributeError, TypeError):
            continue
    placed_share = morning / max(1, morning + afternoon)
    morning_afternoon = 1.0 - abs(placed_share - template.get("morning_share", 0.5))

    def _avg(values):
        return sum(values) / len(values) if values else 1.0

    components = {
        "frequency": round(_avg(freq), 3),
        "day_count": round(_avg(day_count), 3),
        "day_distribution": round(day_dist, 3),
        "time_distribution": round(time_dist, 3),
        "spacing": round(_avg(spacing), 3),
        "practical_pattern": round(practical, 3),
        "break_similarity": round(break_sim, 3),
        "daily_load": round(daily_load, 3),
        "morning_afternoon": round(morning_afternoon, 3),
    }
    components["total"] = round(sum(components.values()) / len(components), 3)
    return components
