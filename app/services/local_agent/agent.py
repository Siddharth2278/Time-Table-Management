"""Phase 1 local agent: learn from previous timetables, store locally.

- Deterministic file analysis (CSV / XLSX / JSON) — no model needed.
- Optional Ollama health reporting (localhost only, never required).
- Phase 2 plugs generation onto get_learning_profile() output.
"""
from pathlib import Path
from typing import Any, Dict, Optional

from app.services.local_agent import pattern_store
from app.services.local_agent.model_client import OllamaClient
from app.services.local_agent.schemas import LearningError, LearningSummary
from app.services.local_agent.timetable_learner import learn, load_rows


class TimetableAgent:
    """Local-first timetable learning agent (Phase 1)."""

    def __init__(self, data_dir: Optional[Path] = None,
                 ollama: Optional[OllamaClient] = None):
        self._data_dir = Path(data_dir) if data_dir is not None else None
        self._ollama = ollama

    def _client(self) -> OllamaClient:
        if self._ollama is None:
            self._ollama = OllamaClient()
        return self._ollama

    def analyze_reference_timetable(self, file_path: str) -> Dict[str, Any]:
        """Learn patterns from a timetable file and save the profile locally.

        Returns a small summary dict. Raises LearningError for invalid
        files or insufficient data. Touches no network.
        """
        rows, skipped = load_rows(file_path)
        profile = learn(rows, source_label=str(file_path))
        saved = pattern_store.save_profile(profile, self._data_dir)
        summary = LearningSummary(
            file=str(file_path),
            lectures=profile["total_lectures"],
            subjects=len(profile["subjects"]),
            roles=len(profile["roles"]),
            skipped_rows=skipped,
        ).as_dict()
        summary["saved_to"] = str(saved)
        summary["ollama_status"] = self._ollama_status()
        return summary

    def get_learning_profile(self) -> Dict[str, Any]:
        """Load the locally stored profile (error when none learned yet)."""
        return pattern_store.load_profile(self._data_dir)

    def clear_learning_profile(self) -> bool:
        """Delete the locally stored profile."""
        return pattern_store.clear_profile(self._data_dir)

    def check_model(self, model: Optional[str] = None) -> Dict[str, Any]:
        """Validate localhost Ollama readiness (raises LearningError if not)."""
        client = self._client()
        active = client.ensure_ready(model)
        return {"running": True, "model": active, "available": True,
                "endpoint": client.endpoint}

    def _ollama_status(self) -> Dict[str, Any]:
        try:
            client = self._client()
            running = client.is_running()
            return {"running": running, "endpoint": client.endpoint,
                    "model": client.model,
                    "model_available": client.is_model_available() if running else False}
        except Exception:
            return {"running": False, "endpoint": "", "model": "",
                    "model_available": False}
