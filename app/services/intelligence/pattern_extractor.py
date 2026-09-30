"""Pattern extraction: turn a ReferenceProfile into scheduling targets."""
from typing import Any, Dict


def extract_patterns(profile: Dict[str, Any]) -> Dict[str, Any]:
    """Deterministic targets derived from reference facts (empty-safe)."""
    day_dist = profile.get("day_distribution", {}) or {}
    time_dist = profile.get("time_distribution", {}) or {}
    total = max(1, profile.get("total_lectures", 0))
    ordered_days = sorted(day_dist, key=lambda d: (-day_dist[d], d))
    ordered_times = sorted(time_dist, key=lambda t: (-time_dist[t], t))
    morning = profile.get("morning_lectures", 0)
    return {
        "preferred_days": ordered_days,
        "preferred_times": ordered_times,
        "day_share": {d: day_dist[d] / total for d in day_dist},
        "time_share": {t: time_dist[t] / total for t in time_dist},
        "morning_share": morning / total,
        "target_daily_load": profile.get("average_daily_lectures", 0.0),
        "wants_consecutive_practicals": profile.get("consecutive_practical_pairs", 0) > 0,
        "break_signature": sorted(
            (b["start"], b["end"]) for b in profile.get("breaks", [])),
        "density_target": profile.get("density", 0.0),
        "has_reference": bool(profile.get("has_data")),
    }
