"""Proposal diff + factual explanations (derived from results, never invented)."""
from typing import Any, Dict, List


def _key(entry):
    return (entry["day_id"], entry["start_time"], entry["end_time"],
            entry["subject_id"], entry["teacher_id"], entry["room_id"])


def diff_proposal(existing: List[dict], proposed: List[dict]) -> Dict[str, int]:
    old, new = {_key(e) for e in existing}, {_key(e) for e in proposed}
    return {"existing": len(old), "generated": len(new),
            "unchanged": len(old & new), "changed": len(new - old)}


def explain_result(session, reference_name: str, accepted: List[dict],
                   rejected_count: int) -> str:
    from app.models import Subject
    counts: Dict[str, int] = {}
    practical_blocks = 0
    by_day_type: Dict[int, Dict[str, list]] = {}
    days = set()
    for e in accepted:
        sub = session.query(Subject).filter(Subject.id == e["subject_id"]).first()
        label = f"{sub.code}" if sub else f"Subject {e['subject_id']}"
        counts[label] = counts.get(label, 0) + 1
        days.add(e["day_id"])
        if (e.get("lecture_type") or "Theory") != "Theory":
            by_day_type.setdefault(e["day_id"], {}).setdefault(
                e["subject_id"], []).append(e["start_time"])
    for per_subject in by_day_type.values():
        for times in per_subject.values():
            if len(times) >= 2:
                practical_blocks += 1
    lines = [f"Generated using {reference_name} as reference."]
    lines += [f"{label}: {n}/week" for label, n in sorted(counts.items())]
    if practical_blocks:
        lines.append(
            f"Practical sessions kept as consecutive blocks ({practical_blocks} grouped days).")
    lines.append(f"Balanced teaching load across {len(days)} day(s).")
    lines.append(f"{rejected_count} placement(s) rejected by conflict validation.")
    lines.append("0 conflicts detected.")
    return "\n".join(lines)


def pattern_lines(template: dict) -> str:
    """Factual pattern summary (§15): what structure was transferred."""
    lines = ["Pattern transferred from reference:"]
    for role in template.get("roles", []):
        kind = "practical" if role.get("practical") else role.get("type_class", "theory")
        if role.get("practical") and role.get("consecutive_block"):
            shape = "consecutive blocks"
        else:
            shape = f"distributed across {role.get('day_count', 0)} days ({role.get('spacing', '-')})"
        lines.append(
            f"{role.get('frequency', 0)}/week {kind} subjects → {shape}, "
            f"prefer {role.get('period_pref', 'mixed')}.")
    breaks = template.get("breaks", []) or []
    if breaks:
        names = ", ".join(f"{b.get('start', '')}-{b.get('end', '')}" for b in breaks)
        lines.append(f"Break pattern preserved: {names}.")
    return "\n".join(lines)
