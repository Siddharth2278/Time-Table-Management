"""Phase 1 local agent: learn from previous timetables, store locally.

- Deterministic file analysis (CSV / XLSX / JSON) — no model needed.
- Optional Ollama health reporting (localhost only, never required).
- Phase 2 plugs generation onto get_learning_profile() output.
"""
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.services.local_agent import pattern_store
from app.services.local_agent.model_client import OllamaClient
from app.services.local_agent.schemas import LearningError, LearningSummary
from app.services.local_agent.timetable_learner import learn, load_rows
from app.services.local_agent.requirements import (
    collect_requirements, learned_to_reference,
)
from app.services.local_agent.schemas import GenerationResult
from app.services.local_agent.planner import (
    build_plan_prompt, parse_plan, plan_to_bias, request_plan,
)


class TimetableAgent:
    """Local-first timetable learning + generation agent (Phases 1+2)."""

    def __init__(self, data_dir: Optional[Path] = None,
                 ollama: Optional[OllamaClient] = None):
        env_dir = os.environ.get("LOCAL_AGENT_DATA_DIR", "")
        if data_dir is not None:
            self._data_dir: Optional[Path] = Path(data_dir)
        elif env_dir.strip():
            self._data_dir = Path(env_dir)
        else:
            self._data_dir = None
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

    def learn_files(self, file_paths: List[str]) -> Dict[str, Any]:
        """Learn from one or more files, merging into the stored profile.

        First file replaces nothing yet merged: it is learned and saved,
        each further file merges via update_profile(). Source history and
        aggregated statistics are preserved.
        """
        if not file_paths:
            raise LearningError("No timetable files given to learn from.")
        combined = None
        total_skipped = 0
        for file_path in file_paths:
            rows, skipped = load_rows(str(file_path))
            total_skipped += skipped
            profile = learn(rows, source_label=str(file_path))
            if combined is None:
                try:
                    existing = pattern_store.load_profile(self._data_dir)
                except LearningError:
                    existing = None
                if existing is None:
                    pattern_store.save_profile(profile, self._data_dir)
                    combined = profile
                else:
                    combined = pattern_store.update_profile(profile, self._data_dir)
            else:
                combined = pattern_store.update_profile(profile, self._data_dir)
        return {
            "files": [str(p) for p in file_paths],
            "lectures": combined["total_lectures"],
            "subjects": len(combined["subjects"]),
            "roles": len(combined["roles"]),
            "skipped_rows": total_skipped,
        }

    def generate_dry_run(self, session, semester_id: int, mode: str = "fill",
                         model: Optional[str] = None,
                         progress=None, avoid: set | None = None,
                         previous_failures: List[str] | None = None,
                         use_model_plan: bool = True) -> GenerationResult:
        """Plan (local model) + solve (existing engine). Writes NOTHING.

        use_model_plan=False runs the template-only path (same solver).
        """
        from app.services.intelligence.timetable_agent import run_intelligence
        learned = self.get_learning_profile()
        requirements = collect_requirements(session, semester_id)
        converted = learned_to_reference(learned)
        bias: Dict[tuple, int] = {}
        dropped: List[str] = []
        model_notes = ""
        planner = "template"
        if use_model_plan:
            client = self._client()
            prompt = build_plan_prompt(requirements, learned, previous_failures)
            raw = request_plan(client, model or client.model, prompt)
            placements, dropped, model_notes = parse_plan(raw, requirements)
            bias = plan_to_bias(placements)
            planner = f"local-model ({model or client.model})"
        out = run_intelligence(session, semester_id, 0, mode, progress,
                               ref_profile=converted, plan=bias or None,
                               avoid=avoid)
        rejected = list(out.get("rejected", []))
        for note in dropped:
            rejected.append({"subject_id": None, "code": "", "name": "",
                             "reason": f"Model row dropped: {note}"})
        hard_conflicts = sum(1 for r in rejected
                             if "onflict" in str(r.get("reason", "")))
        similarity = (out.get("similarity", {}) or {}).get("total", 0.0)
        return GenerationResult(
            accepted=list(out.get("accepted", [])),
            rejected=rejected,
            unplaced=list(out.get("rejected", [])),
            hard_conflicts=hard_conflicts,
            structural_similarity=float(similarity or 0.0),
            profile_info={
                "sources": learned.get("sources", []),
                "lectures": learned.get("total_lectures", 0),
                "roles": len(learned.get("roles", {}) or {}),
                "planner": planner,
                "model_notes": model_notes,
            },
            stats={
                "mode": mode,
                "proposed": len(bias),
                "dropped_rows": len(dropped),
                "validations": out.get("validations", 0),
                "diff": out.get("diff", {}),
            },
        )

    def generate(self, semester_id: int, mode: str = "fill",
                 model: Optional[str] = None, progress=None,
                 avoid: set | None = None,
                 previous_failures: List[str] | None = None,
                 use_model_plan: bool = True) -> GenerationResult:
        """Self-contained dry run (own session, always rolled back)."""
        from app.database import get_session
        session = get_session()
        try:
            return self.generate_dry_run(
                session, semester_id, mode, model, progress, avoid,
                previous_failures, use_model_plan)
        finally:
            try:
                session.close()
            except Exception:
                pass

    def regenerate(self, semester_id: int, previous: GenerationResult,
                   mode: str = "fill", model: Optional[str] = None,
                   progress=None, session=None) -> GenerationResult:
        """New candidate from the same profile: avoids previous cells and
        feeds previous failure reasons back into the model prompt."""
        avoid = {(e["subject_id"], e["day_id"], e["start_time"])
                 for e in (previous.accepted or [])}
        failures = [str(r.get("reason", "")) for r in (previous.rejected or [])]
        failures += [str(r.get("reason", "")) for r in (previous.unplaced or [])]
        if session is None:
            return self.generate(semester_id, mode, model, progress, avoid,
                                 [f for f in failures if f], True)
        return self.generate_dry_run(session, semester_id, mode, model,
                                     progress, avoid,
                                     [f for f in failures if f], True)

    def apply_generation(self, semester_id: int, result: GenerationResult,
                         mode: str = "fill", session=None) -> Dict[str, int]:
        """Atomically commit a dry-run result. Rollback on any failure."""
        from app.database import get_session
        from app.services.intelligence.timetable_agent import apply_result
        if not result.accepted:
            raise LearningError("Nothing to apply: the proposal is empty.")
        own = session is None
        if own:
            session = get_session()
        try:
            return apply_result(session, semester_id,
                                {"accepted": result.accepted}, mode)
        finally:
            if own:
                try:
                    session.close()
                except Exception:
                    pass

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
