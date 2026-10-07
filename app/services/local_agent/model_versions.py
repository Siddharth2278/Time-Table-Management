"""Safe model versioning + rollback for the active timetable model.

Layout (additive, backward compatible)::

    timetable_agent_model/
        model.joblib / metadata.json / training_rows.jsonl  (ACTIVE, legacy)
        manifest.json            (active manifest copy, optional)
        baseline/                (read-only recovery copy from seeding)
        versions/v1/ ...         (snapshots taken before each replacement)
        feedback/feedback.jsonl  (validated local examples awaiting retrain)

Every retrain snapshots the previous working model first; rollback restores
the newest snapshot. A failed replacement never leaves the app model-less.
"""
import json
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.services.local_agent.schemas import LearningError

VERSIONS_DIRNAME = "versions"
FEEDBACK_DIRNAME = "feedback"
FEEDBACK_FILENAME = "feedback.jsonl"
ACTIVE_MANIFEST = "manifest.json"


def versions_dir(data_dir: Optional[Path] = None) -> Path:
    from app.services.local_agent import model_store
    path = model_store.model_dir(data_dir) / VERSIONS_DIRNAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def feedback_dir(data_dir: Optional[Path] = None) -> Path:
    from app.services.local_agent import model_store
    path = model_store.model_dir(data_dir) / FEEDBACK_DIRNAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def _next_version_name(root: Path) -> str:
    existing = 0
    for child in root.iterdir():
        if child.is_dir() and child.name.startswith("v"):
            try:
                existing = max(existing, int(child.name[1:]))
            except ValueError:
                continue
    return f"v{existing + 1}"


def snapshot_version(data_dir: Optional[Path] = None, label: str = "") -> Optional[str]:
    """Snapshot the current ACTIVE model into versions/. No-op when untrained."""
    from app.services.local_agent import model_store
    from app.services.local_agent import pattern_store
    model_path, meta_path, dataset_path = model_store._paths(data_dir)
    if not (model_path.exists() and meta_path.exists()):
        return None
    root = versions_dir(data_dir)
    name = _next_version_name(root)
    dest = root / name
    dest.mkdir(parents=True, exist_ok=True)
    for src in (model_path, meta_path, dataset_path):
        if src.exists():
            shutil.copy2(src, dest / src.name)
    try:
        profile = pattern_store.profile_path(
            Path(data_dir) if data_dir is not None else None)
        if profile.exists():
            shutil.copy2(profile, dest / profile.name)
    except Exception:
        pass
    info = {"version": name, "label": label or "pre-retrain"}
    try:
        info["trained_at"] = json.loads(
            meta_path.read_text(encoding="utf-8")).get("trained_at", "")
    except (OSError, ValueError):
        info["trained_at"] = ""
    with open(dest / "version.json", "w", encoding="utf-8") as fh:
        json.dump(info, fh, indent=1)
    # Keep history bounded; baseline recovery copy is separate and safe.
    kept = sorted_versions(data_dir)[-10:]
    for entry in list_versions(data_dir):
        if entry["version"] not in {k["version"] for k in kept}:
            shutil.rmtree(root / entry["version"], ignore_errors=True)
    return name


def list_versions(data_dir: Optional[Path] = None) -> List[Dict[str, Any]]:
    root = versions_dir(data_dir)
    out = []
    for child in sorted(root.iterdir()):
        if not child.is_dir():
            continue
        info: Dict[str, Any] = {"version": child.name}
        meta = child / "version.json"
        if meta.is_file():
            try:
                info.update(json.loads(meta.read_text(encoding="utf-8")))
            except (OSError, ValueError):
                pass
        try:
            info["files"] = sorted(p.name for p in child.iterdir() if p.is_file())
        except OSError:
            info["files"] = []
        out.append(info)
    return out


def sorted_versions(data_dir: Optional[Path] = None) -> List[Dict[str, Any]]:
    def _key(entry: Dict[str, Any]) -> int:
        try:
            return int(str(entry.get("version", "v0"))[1:])
        except ValueError:
            return 0
    return sorted(list_versions(data_dir), key=_key)


def rollback_to_version(data_dir: Optional[Path] = None,
                        version: Optional[str] = None) -> Dict[str, Any]:
    """Restore ACTIVE from a snapshot (default: newest). Validates after."""
    import os
    from app.services.local_agent import model_store
    from app.services.local_agent import pattern_store
    entries = sorted_versions(data_dir)
    if not entries:
        raise LearningError("No saved model versions to roll back to.")
    wanted = version or entries[-1]["version"]
    src = versions_dir(data_dir) / wanted
    if not src.is_dir():
        raise LearningError(f"Model version '{wanted}' does not exist.")
    model_path, meta_path, dataset_path = model_store._paths(data_dir)
    for name, live in (("model.joblib", model_path), ("metadata.json", meta_path),
                       ("training_rows.jsonl", dataset_path),
                       ("timetable_learning_profile.json",
                        pattern_store.profile_path(data_dir))):
        candidate = src / name
        if candidate.is_file():
            tmp = live.with_name(live.name + ".tmp")
            shutil.copy2(candidate, tmp)
            os.replace(tmp, live)
    model_store.load_model(data_dir)
    return {"restored": wanted}
