"""Current requirement analysis: Required / Scheduled / Remaining per subject."""
from typing import Any, Dict, List

from app.models import Subject, TimetableEntry


def analyze_requirements(session, semester_id: int) -> List[Dict[str, Any]]:
    """Real counts from Subject config + existing entries. Nothing guessed."""
    out = []
    subjects = session.query(Subject).filter(
        Subject.semester_id == semester_id).order_by(Subject.code).all()
    for s in subjects:
        try:
            required = max(0, int(s.required_lectures_per_week or 0))
        except (TypeError, ValueError):
            required = 0
        scheduled = session.query(TimetableEntry).filter(
            TimetableEntry.semester_id == semester_id,
            TimetableEntry.subject_id == s.id).count()
        try:
            duration = int(s.lecture_duration or 60)
        except (TypeError, ValueError):
            duration = 60
        out.append({
            "subject": s,
            "required": required,
            "scheduled": scheduled,
            "remaining": max(0, required - scheduled),
            "duration": duration,
        })
    return out
