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

    def _snapshot_store(self) -> Dict[str, bytes | None]:
        """In-memory backup of model + profile files for post-train rollback."""
        from app.services.local_agent import model_store
        snap: Dict[str, bytes | None] = {}
        try:
            model_path, meta_path, dataset_path = model_store._paths(self._data_dir)
        except Exception:
            return snap
        try:
            profile_path = pattern_store.profile_path(self._data_dir)
        except Exception:
            profile_path = None
        for key, path in (("model", model_path), ("meta", meta_path),
                          ("dataset", dataset_path),
                          ("profile", profile_path) if profile_path else ()):
            try:
                snap[key] = path.read_bytes() if path and path.exists() else None
            except OSError:
                snap[key] = None
        snap["_model_path"] = str(model_path).encode()
        snap["_meta_path"] = str(meta_path).encode()
        snap["_dataset_path"] = str(dataset_path).encode()
        if profile_path is not None:
            snap["_profile_path"] = str(profile_path).encode()
        return snap

    def _restore_snapshot(self, snap: Dict[str, bytes | None]) -> None:
        """Restore files captured by _snapshot_store (best effort)."""
        import os
        from pathlib import Path
        mapping = {"model": "_model_path", "meta": "_meta_path",
                   "dataset": "_dataset_path", "profile": "_profile_path"}
        for key, path_key in mapping.items():
            if path_key not in snap:
                continue
            try:
                path = Path(snap[path_key].decode())
            except Exception:
                continue
            data = snap.get(key)
            try:
                if data is None:
                    if path.exists():
                        path.unlink()
                else:
                    tmp = path.with_name(path.name + ".tmp")
                    tmp.write_bytes(data)
                    os.replace(tmp, path)
            except OSError:
                pass

    def train_agent(self, file_paths: List[str]) -> Dict[str, Any]:
        """Train (or replace-train) the fitted local model from files.

        Builds supervised examples, fits the classifier, validates it,
        reloads it from disk to prove persistence, and only then reports
        success. Previous working model is replaced atomically at the end.
        Profile is rebuilt from the exact stored dataset, so model and
        profile can never describe different data; any post-train failure
        restores the previous files untouched.
        """
        from app.services.local_agent import model_store
        from app.services.local_agent.training_dataset import load_files_as_dicts
        if not file_paths:
            raise LearningError("No timetable files given to train from.")
        rows, skipped, per_file = load_files_as_dicts(file_paths)
        if not rows:
            raise LearningError("No usable lecture rows found for training.")
        snap = self._snapshot_store()
        try:
            report = model_store.train_from_rows(
                rows, source_label=", ".join(str(p) for p in file_paths),
                data_dir=self._data_dir, replace=True)
        except Exception:
            raise
        report["files"] = [str(p) for p in file_paths]
        report["skipped_rows"] = skipped
        report["per_file"] = per_file
        try:
            self._verify_persisted_model(report)
            self._rebuild_profile_from_dataset()
        except Exception:
            self._restore_snapshot(snap)
            raise
        return report

    def update_training(self, file_paths: List[str]) -> Dict[str, Any]:
        """Incremental training: append files to stored rows and retrain."""
        from app.services.local_agent import model_store
        from app.services.local_agent.training_dataset import load_files_as_dicts
        if not file_paths:
            raise LearningError("No timetable files given to train from.")
        rows, skipped, per_file = load_files_as_dicts(file_paths)
        if not rows:
            raise LearningError("No usable lecture rows found for training.")
        snap = self._snapshot_store()
        try:
            report = model_store.train_from_rows(
                rows, source_label=", ".join(str(p) for p in file_paths),
                data_dir=self._data_dir, replace=False)
        except Exception:
            raise
        report["files"] = [str(p) for p in file_paths]
        report["skipped_rows"] = skipped
        report["per_file"] = per_file
        try:
            self._verify_persisted_model(report)
            self._rebuild_profile_from_dataset()
        except Exception:
            self._restore_snapshot(snap)
            raise
        return report

    def _rebuild_profile_from_dataset(self):
        """Rebuild the Phase-1 profile from the exact stored training rows.

        Single source of truth: profile and model.joblib always describe
        the same dataset, so they can never drift apart.
        """
        from app.services.local_agent import model_store
        from app.services.local_agent.schemas import LectureRow
        from app.services.local_agent.timetable_learner import learn
        rows = model_store.dataset_rows(self._data_dir)
        lecture_rows = []
        for raw in rows:
            try:
                lecture_rows.append(LectureRow(
                    code=str(raw.get("code", "")), name=str(raw.get("name", "")),
                    type=str(raw.get("type", "Theory") or "Theory"),
                    duration=int(raw.get("duration", 60) or 60),
                    day=str(raw.get("day", "")), start=str(raw.get("start", "")),
                    end=str(raw.get("end", "")), teacher=str(raw.get("teacher", "")),
                    room=str(raw.get("room", ""))))
            except (TypeError, ValueError):
                continue
        if not lecture_rows:
            return
        sources = sorted({str(r.get("source", "training data")) for r in rows})
        profile = learn(lecture_rows, source_label=", ".join(sources))
        pattern_store.save_profile(profile, self._data_dir)

    def _verify_persisted_model(self, report: Dict[str, Any]):
        """Reload from disk and score one row: proves the saved model works."""
        from app.services.local_agent import model_store
        from app.services.local_agent.training_dataset import FEATURES_V1
        model, metadata = model_store.load_model(self._data_dir)
        if metadata.get("trained_at") != report.get("trained_at"):
            raise LearningError("Persisted model metadata does not match training.")
        scores = model_store.score_candidates(model, [[0.0] * len(FEATURES_V1)])
        if len(scores) != 1:
            raise LearningError("Persisted model failed a prediction check.")
        report["reload_check"] = True

    def model_status(self) -> Dict[str, Any]:
        """Training status of the fitted local model."""
        from app.services.local_agent import model_store
        return model_store.model_status(self._data_dir)

    def clear_model(self) -> bool:
        """Remove the fitted model, metadata and stored training rows."""
        from app.services.local_agent import model_store
        return model_store.clear_model(self._data_dir)

    def _bias_from_trained_model(self, session, requirements: Dict[str, Any],
                                 learned: Dict[str, Any]) -> Dict[tuple, int]:
        """Score candidate cells with the fitted model → ranked bias.

        For each subject needing lectures: map to its learned role, score
        every valid (day, window) cell with assigned staff context, keep
        the top cells as ranks 1..N. The solver still validates everything.
        """
        from app.services.local_agent import model_store
        from app.services.intelligence.candidate_generator import (
            slot_windows_for_duration,
        )
        from app.models import TimeSlot, WorkingDay
        model, _metadata = model_store.load_model(self._data_dir)
        roles = learned.get("roles", {}) or {}
        patterns = learned.get("patterns", {}) or {}
        teacher_load = patterns.get("teacher_workload", {}) or {}
        room_load = patterns.get("room_usage", {}) or {}
        teacher_total = max(1, sum(teacher_load.values()))
        room_total = max(1, sum(room_load.values()))
        days = session.query(WorkingDay).filter(
            WorkingDay.is_enabled == True).order_by(WorkingDay.sort_order).all()  # noqa: E712
        slots = session.query(TimeSlot).filter(
            TimeSlot.is_enabled == True, TimeSlot.is_break == False  # noqa: E712
        ).order_by(TimeSlot.start_time).all()
        day_names = {d.id: d.name for d in days}
        day_load_now: Dict[int, int] = {}
        bias: Dict[tuple, int] = {}
        for item in requirements.get("subjects", []):
            if item["required"] <= 0:
                continue
            role = self._match_learned_role(item, roles)
            if not role:
                continue
            windows = slot_windows_for_duration(slots, item["duration"])
            if not windows:
                continue
            scored = []
            for day in days:
                for start, end in windows:
                    features = self._inference_features(
                        item, role, day, start, day_names, day_load_now,
                        teacher_load, teacher_total, room_load, room_total)
                    scored.append((day.name, start, features))
            try:
                scores = model_store.score_candidates(
                    model, [features for _, _, features in scored])
            except LearningError:
                continue
            ranked = sorted(zip(scored, scores),
                            key=lambda t: (-t[1], t[0][0], t[0][1]))
            for rank, ((day_name, start, _features), _score) in enumerate(ranked[:12], start=1):
                key = (item["id"], day_name, start)
                if key not in bias or rank < bias[key]:
                    bias[key] = rank
        return bias

    @staticmethod
    def _match_learned_role(item: Dict[str, Any], roles: Dict[str, dict]) -> dict:
        """Map a required subject onto a learned role (shape, never names)."""
        cls = "practical" if (item.get("type") or "Theory") != "Theory" else "theory"
        duration = item.get("duration", 60)
        required = item.get("required", 0)
        best = None
        best_cost = None
        for key in sorted(roles):
            role = roles[key]
            cost = (abs(role.get("frequency", 0) - required) * 10
                    + (0 if role.get("type") == cls else 6)
                    + abs(int(role.get("duration", 60) or 60) - duration) / 30.0)
            if best_cost is None or cost < best_cost:
                best_cost = cost
                best = role
        return best or {}

    @staticmethod
    def _inference_features(item, role, day, start, day_names, day_load_now,
                            teacher_load, teacher_total, room_load, room_total):
        """Structural feature vector for one candidate (inference context)."""
        from app.services.local_agent.training_dataset import extract_features
        from app.utils.helpers import time_to_minutes
        try:
            start_min = time_to_minutes(start)
        except (ValueError, AttributeError, TypeError):
            start_min = 9 * 60
        try:
            duration = int(item.get("duration", 60) or 60)
        except (TypeError, ValueError):
            duration = 60
        role_stats = {
            "type_practical": 1 if role.get("type") == "practical" else 0,
            "duration": duration,
            "frequency": item.get("required", 0),
            "avg_gap": role.get("avg_gap", 0.0),
            "morning_share": role.get("morning_share", 0.5),
            "day_count": max(1, int(round(role.get("avg_day_count", 0) or 0))),
            "day_names": list(role.get("preferred_days", []) or []),
            "times": list(role.get("preferred_times", []) or []),
        }
        return extract_features(role_stats, day.sort_order, start_min, {
            "day_load": dict(day_load_now),
            "teacher_share": 0.0,
            "room_share": 0.0,
            "placed_days": [],
            "day_order": {},
            "position_in_day": 0.5,
            "gap_from_break": 1.0,
        }, day_name=day.name, start_str=start)

    def generate_dry_run(self, session, semester_id: int, mode: str = "fill",
                         model: Optional[str] = None,
                         progress=None, avoid: set | None = None,
                         previous_failures: List[str] | None = None,
                         use_model_plan: bool = True,
                         planner: str = "template") -> GenerationResult:
        """Plan + solve (existing engine). Writes NOTHING.

        planner: "template" (deterministic patterns), "local" (Ollama
        preference plan) or "trained" (fitted local model scores).
        use_model_plan=False forces the template path (same solver).
        """
        from app.services.intelligence.timetable_agent import run_intelligence
        learned = self.get_learning_profile()
        requirements = collect_requirements(session, semester_id)
        converted = learned_to_reference(learned)
        bias: Dict[tuple, int] = {}
        dropped: List[str] = []
        model_notes = ""
        planner_name = "template"
        if planner == "trained":
            bias = self._bias_from_trained_model(session, requirements, learned)
            planner_name = "trained-local-model"
        elif use_model_plan:
            client = self._client()
            prompt = build_plan_prompt(requirements, learned, previous_failures)
            raw = request_plan(client, model or client.model, prompt)
            placements, dropped, model_notes = parse_plan(raw, requirements)
            bias = plan_to_bias(placements)
            planner_name = f"local-model ({model or client.model})"
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
                "planner": planner_name,
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
                 use_model_plan: bool = True,
                 planner: str = "template") -> GenerationResult:
        """Self-contained dry run (own session, always rolled back)."""
        from app.database import get_session
        session = get_session()
        try:
            return self.generate_dry_run(
                session, semester_id, mode, model, progress, avoid,
                previous_failures, use_model_plan, planner)
        finally:
            try:
                session.close()
            except Exception:
                pass

    def regenerate(self, semester_id: int, previous: GenerationResult,
                   mode: str = "fill", model: Optional[str] = None,
                   progress=None, session=None,
                   planner: str = "template") -> GenerationResult:
        """New candidate from the same profile: avoids previous cells and
        feeds previous failure reasons back into the model prompt."""
        avoid = {(e["subject_id"], e["day_id"], e["start_time"])
                 for e in (previous.accepted or [])}
        failures = [str(r.get("reason", "")) for r in (previous.rejected or [])]
        failures += [str(r.get("reason", "")) for r in (previous.unplaced or [])]
        use_model = planner == "local"
        if session is None:
            return self.generate(semester_id, mode, model, progress, avoid,
                                 [f for f in failures if f], use_model,
                                 planner)
        return self.generate_dry_run(session, semester_id, mode, model,
                                     progress, avoid,
                                     [f for f in failures if f], use_model,
                                     planner)

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
