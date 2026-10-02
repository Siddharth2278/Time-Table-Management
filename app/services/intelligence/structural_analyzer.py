"""Deep structural analysis of one reference timetable.

Per-subject shape (not just counts): exact days/times, gaps, morning /
afternoon split, consecutive-day behavior, practical blocks, break
relations, preferred ranges. Fully deterministic, read-only.
"""
from typing import Any, Dict, List

from app.models import Subject, TimetableEntry, WorkingDay
from app.utils.helpers import time_to_minutes


def _day_order(session) -> Dict[str, int]:
    days = session.query(WorkingDay).order_by(WorkingDay.sort_order).all()
    return {d.name: d.sort_order for d in days}


def analyze_structure(session, semester_id: int) -> Dict[str, Any]:
    """Return {subjects: [...deep stats...], day_load, meta} for a semester."""
    order = _day_order(session)
    entries = session.query(TimetableEntry).filter(
        TimetableEntry.semester_id == semester_id).all()
    by_subject: Dict[int, list] = {}
    for e in entries:
        by_subject.setdefault(e.subject_id, []).append(e)

    subjects = []
    for subject_id, rows in sorted(by_subject.items()):
        sub = session.query(Subject).filter(Subject.id == subject_id).first()
        days = sorted({_day_name(session, r.day_id) for r in rows})
        day_idx = sorted(order.get(_day_name(session, r.day_id), 999) for r in rows)
        starts = sorted(r.start_time for r in rows)
        morning = afternoon = 0
        minutes = []
        for r in rows:
            try:
                mins = time_to_minutes(r.start_time)
            except (ValueError, AttributeError, TypeError):
                continue
            minutes.append(mins)
            if mins < 12 * 60:
                morning += 1
            else:
                afternoon += 1
        gaps = [b - a for a, b in zip(sorted(set(day_idx)), sorted(set(day_idx))[1:])]
        consecutive_pairs = sum(1 for a, b in zip(sorted(set(day_idx)), sorted(set(day_idx))[1:]) if b - a == 1)
        types = {r.lecture_type or "Theory" for r in rows}
        practical_rows = [r for r in rows if (r.lecture_type or "Theory") != "Theory"]
        block_lengths = _block_lengths(practical_rows)
        subjects.append({
            "subject_id": subject_id,
            "code": sub.code if sub else f"Sub {subject_id}",
            "name": sub.name if sub else "",
            "type_class": "practical" if any(
                (r.lecture_type or "Theory") != "Theory" for r in rows) else "theory",
            "total": len(rows),
            "pct": 0.0,  # filled below against weekly total
            "days": days,
            "day_count": len(days),
            "day_indexes": sorted(set(day_idx)),
            "gaps": gaps,
            "avg_gap": round(sum(gaps) / len(gaps), 2) if gaps else 0.0,
            "consecutive_pairs": consecutive_pairs,
            "avoids_consecutive": consecutive_pairs == 0 and len(days) > 1,
            "times": starts,
            "morning": morning,
            "afternoon": afternoon,
            "period_pref": ("morning" if morning > afternoon else
                            "afternoon" if afternoon > morning else "mixed"),
            "avg_time": _fmt(sum(minutes) // len(minutes)) if minutes else "",
            "earliest": min(starts) if starts else "",
            "latest": max(starts) if starts else "",
            "max_per_day": max([len([r for r in rows if _day_name(session, r.day_id) == d])
                                for d in days] or [0]),
            "practical_blocks": block_lengths,
            "has_consecutive_block": any(length >= 2 for length in block_lengths),
            "duration": sub.lecture_duration if sub else 60,
        })
    total = max(1, len(entries))
    for s in subjects:
        s["pct"] = round(s["total"] / total, 3)
    day_load: Dict[str, int] = {}
    for e in entries:
        name = _day_name(session, e.day_id)
        day_load[name] = day_load.get(name, 0) + 1
    return {"subjects": sorted(subjects, key=lambda s: (-s["total"], s["code"])),
            "day_load": day_load, "total": len(entries)}


def _day_name(session, day_id):
    day = session.query(WorkingDay).filter(WorkingDay.id == day_id).first()
    return day.name if day else f"Day {day_id}"


def _fmt(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def _block_lengths(practical_rows) -> List[int]:
    """Consecutive same-day practical runs (by adjacent start times)."""
    by_day: Dict[Any, list] = {}
    for r in practical_rows:
        try:
            by_day.setdefault(r.day_id, []).append(time_to_minutes(r.start_time))
        except (ValueError, AttributeError, TypeError):
            continue
    lengths = []
    for times in by_day.values():
        ordered = sorted(times)
        run, best = 1, 1
        for a, b in zip(ordered, ordered[1:]):
            if 0 < b - a <= 70:
                run += 1
                best = max(best, run)
            else:
                run = 1
        lengths.append(best)
    return lengths
