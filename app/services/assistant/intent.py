"""Rule-based intent parser (offline, deterministic, no LLM required).

Maps typed or transcribed utterances onto the strict tool layer. Unknown or
ambiguous input yields a clarification request instead of a guess. The
conversational model (Ollama, optional) is only ever used to phrase the
final response; tool selection here is exact and testable.
"""
import re
from typing import Any, Dict, Optional

_PATTERNS = [
    (r"generate.*semester\s*(?P<semester>\d+)", "generate_timetable",
     lambda m: {"semester": f"Semester {m.group('semester')}"}),
    (r"regenerate.*semester\s*(?P<semester>\d+)", "generate_timetable",
     lambda m: {"semester": f"Semester {m.group('semester')}"}),
    (r"show.*semester\s*(?P<semester>\d+).*timetable", "show_semester_timetable",
     lambda m: {"semester": f"Semester {m.group('semester')}"}),
    (r"today'?s timetable|timetable.*today|show.*today", "show_today_timetable",
     lambda m: {}),
    (r"(?P<teacher>[\w .]+?)\s+free.*?(?P<day>monday|tuesday|wednesday|thursday|friday|saturday|sunday).*?(?P<time>\d{1,2}(?::\d{2})?\s*(?:am|pm)?)",
     "teacher_free_at", lambda m: {"teacher": m.group("teacher").strip(),
                                   "day": m.group("day").capitalize(),
                                   "time": m.group("time")}),
    (r"who.*unavailable.*?(?P<day>monday|tuesday|wednesday|thursday|friday|saturday|sunday)",
     "who_unavailable", lambda m: {"day": m.group("day").capitalize()}),
    (r"unavailable.*?(?P<day>monday|tuesday|wednesday|thursday|friday|saturday|sunday)",
     "who_unavailable", lambda m: {"day": m.group("day").capitalize()}),
    (r"move.*?lecture\s*(?P<entry>\d+).*?(?P<day>monday|tuesday|wednesday|thursday|friday|saturday|sunday).*?(?P<start>\d{1,2}:\d{2}).*?(?P<end>\d{1,2}:\d{2})",
     "move_lecture", lambda m: {"entry_id": int(m.group("entry")),
                                "day": m.group("day").capitalize(),
                                "start": m.group("start"),
                                "end": m.group("end")}),
    (r"add.*teacher.*?(?:named\s+)?(?P<name>[a-z][\w .]+)", "create_teacher",
     lambda m: {"name": m.group("name").strip().title()}),
    (r"add.*room.*?(?P<name>[\w \-]+)", "create_room",
     lambda m: {"name": m.group("name").strip()}),
    (r"add.*subject.*?(?P<code>[A-Za-z]{2,}\d+)", "create_subject",
     lambda m: {"code": m.group("code").upper(),
                "name": m.group("code").upper(), "semester": "Semester 1"}),
    (r"(available|free).*lab", "find_available_lab",
     lambda m: {"day": "Monday", "start": "09:00", "end": "10:00"}),
    (r"conflict", "show_conflicts", lambda m: {}),
    (r"why.*(place|lecture\s*(?P<entry>\d+))", "explain_placement",
     lambda m: {"entry_id": int(m.group("entry") or 0) or 1}),
    (r"training status|ai training|model status", "training_status",
     lambda m: {}),
    (r"update.*ai|retrain|update.*agent", "update_agent", lambda m: {}),
    (r"export.*semester\s*(?P<semester>\d+).*pdf", "export_pdf",
     lambda m: {"semester": f"Semester {m.group('semester')}"}),
    (r"backup", "backup_data", lambda m: {}),
    (r"restore", "restore_backup", lambda m: {}),
]

_DESTRUCTIVE = re.compile(
    r"(delete all|clear (teachers|rooms|subjects)|replace.*timetable|"
    r"delete.*semester\s*\d+.*timetable)", re.IGNORECASE)


def parse(text: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Return {tool, params} or {clarify} or {confirm} dict. Never raises."""
    raw = (text or "").strip()
    lowered = raw.lower()
    if not lowered:
        return {"clarify": "What would you like to do?"}
    if _DESTRUCTIVE.search(lowered):
        return {"confirm": "Do you want me to delete all Semester 4 timetable "
                           "entries? Please reply Yes to confirm.",
                "pending_tool": "clear_timetable",
                "pending_params": {"semester": "Semester 4"}}
    # "Move this ..." resolves against the selected lecture in context.
    if re.search(r"move this", lowered):
        entry = (context or {}).get("selected_entry_id")
        day_m = re.search(
            r"(monday|tuesday|wednesday|thursday|friday|saturday|sunday)",
            lowered)
        time_m = re.search(r"(\d{1,2}:\d{2}).*?(\d{1,2}:\d{2})", lowered)
        if entry and day_m and time_m:
            return {"tool": "move_lecture",
                    "params": {"entry_id": int(entry),
                               "day": day_m.group(1).capitalize(),
                               "start": time_m.group(1),
                               "end": time_m.group(2)}}
        return {"clarify": "Which lecture should I move, and to which "
                           "day and time?"}
    for pattern, tool, build in _PATTERNS:
        match = re.search(pattern, lowered)
        if match:
            try:
                return {"tool": tool, "params": build(match)}
            except (IndexError, ValueError, AttributeError):
                continue
    return {"clarify": "I can generate timetables, show schedules, check "
                       "availability and conflicts, move lectures, add "
                       "teachers/rooms/subjects, export PDF, back up data, "
                       "or report training status. What should I do?"}
