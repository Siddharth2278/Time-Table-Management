"""Subject role mapping: match by SHAPE (frequency/type/duration), never by name.

A 4/week Theory subject inherits the 4-lecture theory pattern no matter
whether it is called Mathematics or Computer Networks. Closest valid
pattern wins when nothing matches exactly.
"""
from typing import Any, Dict, List


def _type_class(subject_type: str) -> str:
    return "practical" if (subject_type or "Theory") != "Theory" else "theory"


def _subject_duration(subject) -> int:
    try:
        return int(subject.lecture_duration or 60)
    except (TypeError, ValueError):
        return 60


def map_roles(target_subjects: List[Any], roles: List[dict]) -> Dict[int, dict]:
    """Return {subject_id: role}. Deterministic; ties break by template order.

    Roles are consumed 1:1 (first subject in code order takes its best
    remaining role) so two 4/week subjects inherit two DIFFERENT 4/week
    patterns instead of collapsing onto the first one. When roles run
    out, the closest role may be shared.
    """
    mapping: Dict[int, dict] = {}
    used: set = set()

    def _cost(subject, required, cls, duration, role):
        count_cost = abs(role.get("frequency", 0) - required) * 10
        class_cost = 0 if role.get("type_class") == cls else 6
        try:
            dur_cost = abs(int(role.get("duration") or 60) - duration) / 30.0
        except (TypeError, ValueError):
            dur_cost = 2.0
        return count_cost + class_cost + dur_cost

    def _spec(subject):
        try:
            required = max(0, int(subject.required_lectures_per_week or 0))
        except (TypeError, ValueError):
            required = 0
        return required, _type_class(subject.subject_type), _subject_duration(subject)

    for subject in sorted(target_subjects, key=lambda s: (s.code or "")):
        required, cls, duration = _spec(subject)
        need = ((subject.room_requirement or "").strip().lower()
                if hasattr(subject, "room_requirement") else "")
        if required <= 0 or not roles:
            mapping[subject.id] = {}
            continue
        pool = [(o, r) for o, r in enumerate(roles) if o not in used] or list(enumerate(roles))
        scored = sorted(((_cost(subject, required, cls, duration, role), order)
                         for order, role in pool),
                        key=lambda t: (t[0], t[1]))
        _, order = scored[0]
        used.add(order)
        best = roles[order]
        mapping[subject.id] = {
            **best,
            "required": required,
            "type_class": cls,
            "duration": duration,
            "room_requirement": need,
        }
    return mapping
