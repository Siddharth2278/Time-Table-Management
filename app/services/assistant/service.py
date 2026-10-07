"""Assistant service: typed/voice text -> intent -> strict tools -> response.

Rule-based intent selection runs locally (no network). An optional local
Ollama model may polish wording when AI Data Mode allows it, but tool
choice and execution never depend on it. Destructive actions require an
explicit Yes; reads never do.
"""
from typing import Any, Dict, Optional

from app.services.assistant import intent as _intent
from app.services.assistant import tools as _tools
from app.services.local_agent.schemas import LearningError


class AssistantService:
    """Stateful per-dialog assistant (pending confirmations live here)."""

    def __init__(self, context: Optional[Dict[str, Any]] = None):
        self.context: Dict[str, Any] = dict(context or {})
        self._pending: Optional[Dict[str, Any]] = None
        self.history: list = []

    def set_context(self, context: Dict[str, Any]) -> None:
        self.context.update(context or {})

    # ---- main entry -------------------------------------------------
    def handle_text(self, text: str) -> Dict[str, Any]:
        """Handle one user message. Returns {reply, ...}. Never raises."""
        raw = (text or "").strip()
        if not raw:
            return {"reply": "What would you like to do?"}
        lowered = raw.lower()
        # Confirmation flow for a pending destructive action.
        if self._pending is not None:
            if lowered in ("yes", "yes please", "confirm", "do it"):
                pending, self._pending = self._pending, None
                return self._execute_pended(pending)
            if lowered in ("no", "cancel", "stop", "never mind"):
                self._pending = None
                return {"reply": "Cancelled. Nothing was changed."}
            self._pending = None  # new request overrides the pending one.
        try:
            parsed = _intent.parse(raw, self.context)
        except Exception:
            parsed = {"clarify": "Sorry, I did not understand that."}
        if "clarify" in parsed:
            reply = str(parsed["clarify"])
            self._remember(raw, reply)
            return {"reply": self._polish(reply)}
        if "confirm" in parsed:
            self._pending = {"tool": parsed.get("pending_tool", ""),
                             "params": parsed.get("pending_params", {})}
            reply = str(parsed["confirm"])
            self._remember(raw, reply)
            return {"reply": reply, "needs_confirmation": True}
        return self._run_tool(raw, str(parsed.get("tool", "")),
                              dict(parsed.get("params", {})))

    # ---- execution --------------------------------------------------
    def _run_tool(self, raw: str, tool: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if _tools.needs_confirmation(tool):
            self._pending = {"tool": tool, "params": params}
            reply = "This is destructive. Please reply Yes to confirm."
            self._remember(raw, reply)
            return {"reply": reply, "needs_confirmation": True}
        try:
            if tool in ("export_pdf", "backup_data", "restore_backup",
                        "clear_timetable"):
                result = self._run_extended(tool, params)
            else:
                result = _tools.dispatch(tool, params)
        except LearningError as e:
            reply = str(e)
            self._remember(raw, reply)
            return {"reply": reply}
        except Exception:
            reply = "That operation failed. Nothing was changed."
            self._remember(raw, reply)
            return {"reply": reply}
        reply = self._describe(tool, params, result)
        self._remember(raw, reply)
        out = {"reply": self._polish(reply), "tool": tool, "result": result}
        return out

    def _execute_pended(self, pending: Dict[str, Any]) -> Dict[str, Any]:
        tool, params = pending.get("tool", ""), pending.get("params", {})
        try:
            result = self._run_extended(tool, params) if tool in (
                "export_pdf", "backup_data", "restore_backup",
                "clear_timetable") else _tools.dispatch(tool, params)
        except LearningError as e:
            return {"reply": str(e)}
        except Exception:
            return {"reply": "That operation failed. Nothing was changed."}
        return {"reply": self._polish(
            self._describe(tool, params, result)), "tool": tool,
            "result": result}

    def _run_extended(self, tool: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if tool == "export_pdf":
            from app.database import get_session
            from app.models import Semester
            session = get_session()
            try:
                name = str(params.get("semester", "Semester 1"))
                sem = session.query(Semester).filter(
                    Semester.name == name).first()
                if sem is None:
                    raise LearningError(f"Semester '{name}' was not found.")
                return {"exported": name, "semester_id": sem.id,
                        "hint": "Use Timetable view Export for the PDF file."}
            finally:
                try:
                    session.close()
                except Exception:
                    pass
        if tool == "backup_data":
            return {"backed_up": True,
                    "hint": "Use Backup view to choose the backup file."}
        if tool == "restore_backup":
            raise LearningError(
                "Restore replaces all current data. Pick the backup file in "
                "the Backup view to continue.")
        if tool == "clear_timetable":
            from app.database import get_session
            from app.models import TimetableEntry
            session = get_session()
            try:
                from app.models import Semester
                sem = session.query(Semester).filter(
                    Semester.name == str(params.get("semester",
                                                    "Semester 4"))).first()
                if sem is None:
                    raise LearningError("Semester was not found.")
                count = session.query(TimetableEntry).filter(
                    TimetableEntry.semester_id == sem.id).count()
                return {"semester": sem.name, "entries": count,
                        "hint": "Confirm to delete; use Timetable view otherwise."}
            finally:
                try:
                    session.close()
                except Exception:
                    pass
        raise LearningError(f"Unknown assistant action '{tool}'.")

    # ---- responses --------------------------------------------------
    @staticmethod
    def _describe(tool: str, params: Dict[str, Any],
                  result: Dict[str, Any]) -> str:
        try:
            if tool == "generate_timetable":
                return (f"{result.get('semester', '')} timetable draft: "
                        f"{result.get('accepted', 0)} lectures accepted, "
                        f"{result.get('unplaced', 0)} unplaced "
                        f"(planner {result.get('planner', '')}). "
                        "Review it in Timetable Intelligence before applying.")
            if tool == "show_semester_timetable":
                return (f"{result.get('semester', '')} has "
                        f"{result.get('count', 0)} scheduled lectures.")
            if tool == "show_today_timetable":
                return (f"{result.get('day', '')}: "
                        f"{result.get('count', 0)} lectures scheduled.")
            if tool == "teacher_free_at":
                return ("Yes, free." if result.get("free") else
                        f"Not free (busy {', '.join(result.get('busy', []))}).")
            if tool == "who_unavailable":
                names = result.get("unavailable", [])
                return ("Nobody is marked unavailable on "
                        f"{result.get('day', '')}." if not names else
                        f"Unavailable on {result.get('day', '')}: "
                        + "; ".join(names))
            if tool == "move_lecture":
                return (f"Lecture {result.get('moved')} moved to "
                        f"{result.get('day')} {result.get('time')}.")
            if tool in ("create_teacher", "create_room", "create_subject"):
                return f"Added {result.get('created')}."
            if tool == "find_available_lab":
                labs = result.get("labs", [])
                return ("No free lab at that time." if not labs else
                        "Free labs: " + ", ".join(labs))
            if tool == "show_conflicts":
                if not result.get("count"):
                    return "No timetable conflicts found."
                return ("Conflicts: "
                        + "; ".join(result.get("conflicts", [])))
            if tool == "explain_placement":
                return str(result.get("explanation", ""))
            if tool == "training_status":
                return (f"Pending examples: {result.get('pending', 0)}, "
                        f"trained: {result.get('trained')}, "
                        f"model v{result.get('model_version', '?')}.")
            if tool == "update_agent":
                return ("Agent retrained." if result.get("retrained") else
                        f"Not yet: {result.get('pending', 0)}/"
                        f"{result.get('min_examples', '?')} examples.")
            if tool == "clear_timetable":
                return (f"{result.get('semester', '')} has "
                        f"{result.get('entries', 0)} entries. "
                        "Deletion is performed in the Timetable view "
                        "after confirmation.")
            if tool == "export_pdf":
                return (f"{result.get('semester', '')} is ready to export. "
                        "Use Timetable view Export for the PDF file.")
            if tool == "backup_data":
                return "Use the Backup view to choose the backup file."
            return "Done."
        except Exception:
            return "Done."

    def _polish(self, reply: str) -> str:
        """Optional local-Ollama wording polish; rule-based reply otherwise."""
        try:
            from app.services.local_agent.adaptive import get_setting
            if (get_setting("ai_data_mode") or "local") != "local":
                return reply  # external mode has no provider; keep local text.
            from app.services.local_agent.model_client import OllamaClient
            client = OllamaClient()
            if not client.is_running():
                return reply
            # Keep it short and factual; any failure keeps the base reply.
            polished = client.generate(
                "Rephrase briefly for a timetable app user, keep all facts. "
                f"Text: {reply}", options={"temperature": 0.1,
                                           "num_predict": 120})
            return polished.strip() or reply
        except Exception:
            return reply

    def _remember(self, user: str, assistant: str) -> None:
        self.history.append({"you": user, "ai": assistant})
        self.history = self.history[-50:]
