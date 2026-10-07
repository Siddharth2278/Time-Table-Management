"""Verified baseline agent: export / validate / seed.

The baseline is an explicitly exported, genuinely fitted model package that
may be bundled with the installer. It is NEVER random APPDATA contents.

Source layout (admin PC)::

    agent_seed/  (or assets/baseline_agent/)
        model.joblib
        metadata.json
        training_rows.jsonl
        timetable_learning_profile.json
        manifest.json

On first launch with no active model, the bundled baseline is copied to
``%APPDATA%\\CollegeTimetableManager`` as the ACTIVE model plus a
read-only recovery copy under ``timetable_agent_model/baseline/``.
Program Files is never written at runtime.

Backward compatibility: the active model keeps the legacy flat paths
``timetable_agent_model/model.joblib|metadata.json|training_rows.jsonl``
so every existing test and caller keeps working. ``baseline/``,
``versions/`` and ``feedback/`` are additive siblings.
"""
import hashlib
import json
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.services.local_agent.schemas import LearningError
from app.services.local_agent.trainable_model import MODEL_VERSION
from app.services.local_agent.training_dataset import FEATURE_SCHEMA_VERSION

BASELINE_FILENAMES = (
    "model.joblib",
    "metadata.json",
    "training_rows.jsonl",
    "timetable_learning_profile.json",
)
MANIFEST_FILENAME = "manifest.json"
PACKAGE_FORMAT = 1


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_manifest(files: Dict[str, Path], extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Manifest dict with checksums for the given {filename: path} set."""
    from app.services.local_agent.model_store import _utcnow
    checksums = {}
    for name, path in files.items():
        try:
            checksums[name] = _sha256(path)
        except OSError as e:
            raise LearningError(f"Cannot checksum baseline file '{path}': {e}")
    manifest: Dict[str, Any] = {
        "package_format": PACKAGE_FORMAT,
        "model_version": MODEL_VERSION,
        "feature_schema": FEATURE_SCHEMA_VERSION,
        "checksums": checksums,
    }
    if extra:
        manifest.update(extra)
    return manifest


def _sanitize_sources(raw_sources) -> Dict[str, Any]:
    """Release-safe source labels: basenames only, never local paths.

    Absolute developer paths (which can expose usernames) are reduced to
    file names plus a file count. Returns {"sources": [...], "source_files": n}.
    """
    names: List[str] = []
    for item in raw_sources or []:
        label = str(item or "").strip()
        if not label:
            continue
        # Split multi-file labels such as "a.csv, b.csv".
        for part in re.split(r"\s*,\s*", label):
            part = part.strip()
            if not part:
                continue
            # Strip directories, drive letters and URI prefixes.
            part = part.replace("\\", "/")
            name = part.rsplit("/", 1)[-1]
            if name and name not in names:
                names.append(name)
    return {"sources": names, "source_files": len(names)}


def export_baseline(data_dir: Optional[Path] = None,
                    out_dir: Optional[Path] = None,
                    kind: str = "production") -> Dict[str, Any]:
    """Export the current ACTIVE model as a verified baseline package.

    kind is "production" (trained on real college histories) or "sample"
    (development data only; never ship as a production model). Release
    metadata is sanitized: only file basenames and counts are recorded,
    never absolute local paths.

    Validates the model is genuinely fitted (reload + score check) before
    writing anything. Returns {"out_dir": ..., "manifest": ...}.
    """
    from app.database import get_data_dir
    from app.services.local_agent import model_store, pattern_store
    if kind not in ("production", "sample"):
        raise LearningError("Baseline kind must be 'production' or 'sample'.")
    base = Path(data_dir) if data_dir is not None else get_data_dir()
    model_path, meta_path, dataset_path = model_store._paths(base)
    profile_path = pattern_store.profile_path(base)
    for path in (model_path, meta_path, dataset_path, profile_path):
        if not path.exists():
            raise LearningError(
                f"Cannot export baseline: missing '{path.name}'. "
                "Train the agent first.")
    # Genuinely fitted check: reload + score + metadata versions.
    model, metadata = model_store.load_model(base)
    profile = pattern_store.load_profile(base)
    if metadata.get("model_version") != MODEL_VERSION:
        raise LearningError("Active model version is incompatible; cannot export.")
    if metadata.get("feature_schema") != FEATURE_SCHEMA_VERSION:
        raise LearningError("Active feature schema is incompatible; cannot export.")
    scores = model_store.score_candidates(model, [[0.0] * len(
        __import__("app.services.local_agent.training_dataset", fromlist=["FEATURES_V1"]).FEATURES_V1)])
    if len(scores) != 1:
        raise LearningError("Active model failed a prediction check; cannot export.")
    if int(metadata.get("lectures", 0) or 0) <= 0:
        raise LearningError("Active model has no training data; cannot export.")
    dest = Path(out_dir) if out_dir is not None else base / "agent_seed"
    dest.mkdir(parents=True, exist_ok=True)
    mapping = {
        "model.joblib": model_path,
        "metadata.json": meta_path,
        "training_rows.jsonl": dataset_path,
        "timetable_learning_profile.json": profile_path,
    }
    for name, src in mapping.items():
        shutil.copy2(src, dest / name)
    sanitized = _sanitize_sources(
        metadata.get("sources", profile.get("sources", [])))
    manifest = build_manifest(
        {name: dest / name for name in mapping},
        extra={
            "baseline_kind": kind,
            "trained_at": metadata.get("trained_at", ""),
            "lectures": metadata.get("lectures", profile.get("total_lectures", 0)),
            "positives": metadata.get("positives", 0),
            "negatives": metadata.get("negatives", 0),
            "backend": metadata.get("backend", ""),
            "train_seconds": metadata.get("train_seconds"),
            "separation": metadata.get("separation"),
            "sources": sanitized["sources"],
            "source_files": sanitized["source_files"],
            "exported_at": model_store._utcnow(),
            "compatibility": {"min_app_version": "1.1.0", "python": "3.x"},
        },
    )
    with open(dest / MANIFEST_FILENAME, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=1)
    return {"out_dir": str(dest), "manifest": manifest}


def validate_baseline_dir(path: Path) -> Dict[str, Any]:
    """Validate a baseline package directory. Returns its manifest."""
    root = Path(path)
    for name in BASELINE_FILENAMES + (MANIFEST_FILENAME,):
        if not (root / name).is_file():
            raise LearningError(f"Baseline package is missing '{name}'.")
    try:
        manifest = json.loads((root / MANIFEST_FILENAME).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise LearningError(f"Baseline manifest is unreadable: {e}")
    if not isinstance(manifest, dict) or manifest.get("package_format") != PACKAGE_FORMAT:
        raise LearningError("Baseline package has an unsupported format.")
    if manifest.get("model_version") != MODEL_VERSION:
        raise LearningError("Baseline model version is incompatible with this app.")
    if manifest.get("feature_schema") != FEATURE_SCHEMA_VERSION:
        raise LearningError("Baseline feature schema is incompatible with this app.")
    checksums = manifest.get("checksums", {})
    if not isinstance(checksums, dict):
        raise LearningError("Baseline manifest has no integrity information.")
    for name in BASELINE_FILENAMES:
        expected = checksums.get(name)
        if not expected:
            raise LearningError(f"Baseline manifest has no checksum for '{name}'.")
        actual = _sha256(root / name)
        if actual != expected:
            raise LearningError(
                f"Baseline file '{name}' failed integrity check "
                "(checksum mismatch).")
    try:
        metadata = json.loads((root / "metadata.json").read_text(encoding="utf-8"))
        profile = json.loads((root / "timetable_learning_profile.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise LearningError(f"Baseline metadata/profile unreadable: {e}")
    if metadata.get("lectures") is None:
        raise LearningError("Baseline metadata has no lecture count.")
    # training_rows line count must match metadata lectures.
    lines = sum(1 for _ in open(root / "training_rows.jsonl", encoding="utf-8") if _.strip())
    if lines != metadata.get("lectures"):
        raise LearningError("Baseline dataset does not match its metadata.")
    if not isinstance(profile, dict) or "total_lectures" not in profile:
        raise LearningError("Baseline learning profile is invalid.")
    return manifest


def find_bundled_baseline() -> Optional[Path]:
    """Bundled read-only baseline, if the installer included one."""
    candidates: List[Path] = []
    try:
        base = getattr(sys, "_MEIPASS", None)
        if base:
            candidates.append(Path(base) / "assets" / "baseline_agent")
    except Exception:
        pass
    here = Path(__file__).resolve()
    candidates.append(here.parents[4] / "assets" / "baseline_agent")
    candidates.append(Path.cwd() / "assets" / "baseline_agent")
    for path in candidates:
        try:
            if path.is_dir() and (path / MANIFEST_FILENAME).is_file():
                return path
        except Exception:
            continue
    return None


def baseline_recovery_dir(data_dir: Optional[Path] = None) -> Path:
    from app.database import get_data_dir
    from app.services.local_agent import model_store
    root = model_store.model_dir(Path(data_dir) if data_dir is not None else get_data_dir())
    path = root / "baseline"
    path.mkdir(parents=True, exist_ok=True)
    return path


def export_package(data_dir: Optional[Path] = None,
                   zip_path: Optional[Path] = None) -> Dict[str, Any]:
    """Export the active agent as CollegeTimetableAgentPackage.zip."""
    import tempfile
    import zipfile
    info = export_baseline(data_dir, Path(tempfile.mkdtemp(prefix="ctm-agent-")))
    src = Path(info["out_dir"])
    dest = Path(zip_path) if zip_path is not None else Path(
        str(src) + ".zip").with_name("CollegeTimetableAgentPackage.zip")
    dest.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in BASELINE_FILENAMES + (MANIFEST_FILENAME,):
            archive.write(src / name, arcname=name)
    try:
        shutil.rmtree(src, ignore_errors=True)
    except OSError:
        pass
    return {"zip": str(dest), "manifest": info["manifest"]}


def import_package(zip_path: Path,
                   data_dir: Optional[Path] = None) -> Dict[str, Any]:
    """Validate + activate an agent zip (data files only, never code)."""
    import tempfile
    import zipfile
    src = Path(zip_path)
    if not src.is_file():
        raise LearningError(f"Agent package '{src}' was not found.")
    tmp = Path(tempfile.mkdtemp(prefix="ctm-agent-import-"))
    try:
        with zipfile.ZipFile(src, "r") as archive:
            names = set(archive.namelist())
            for name in BASELINE_FILENAMES + (MANIFEST_FILENAME,):
                if name not in names:
                    raise LearningError(
                        f"Agent package is missing '{name}'.")
            for name in names:
                if name.endswith((".py", ".exe", ".dll", ".so", ".bat",
                                   ".ps1", ".sh")):
                    raise LearningError(
                        f"Agent package contains executable '{name}'; "
                        "only model/data files are allowed.")
            archive.extractall(tmp)
        manifest = validate_baseline_dir(tmp)
    except LearningError:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    except Exception as e:
        shutil.rmtree(tmp, ignore_errors=True)
        raise LearningError(f"Agent package is unreadable: {e}")
    from app.database import get_data_dir
    from app.services.local_agent import model_store, pattern_store
    base = Path(data_dir) if data_dir is not None else get_data_dir()
    try:
        from app.services.local_agent import model_versions
        model_versions.snapshot_version(base, label="pre-import")
    except Exception:
        pass
    model_path, meta_path, dataset_path = model_store._paths(base)
    shutil.copy2(tmp / "model.joblib", model_path)
    shutil.copy2(tmp / "metadata.json", meta_path)
    shutil.copy2(tmp / "training_rows.jsonl", dataset_path)
    shutil.copy2(tmp / "timetable_learning_profile.json",
                 pattern_store.profile_path(base))
    shutil.rmtree(tmp, ignore_errors=True)
    model_store.load_model(base)
    try:
        from app.services.local_agent.baseline import clear_seed_info
        clear_seed_info(base)  # user-imported package, not the bundled baseline.
    except Exception:
        pass
    return {"manifest": manifest, "restored": True}


def seed_active_from_baseline(data_dir: Optional[Path] = None,
                              bundled: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """First-launch seeding: bundled baseline -> active model + recovery copy.

    Never overwrites an existing active model. Returns manifest info or None
    when there is nothing to seed from.
    """
    from app.database import get_data_dir
    from app.services.local_agent import model_store, pattern_store
    base = Path(data_dir) if data_dir is not None else get_data_dir()
    model_path, meta_path, dataset_path = model_store._paths(base)
    if model_path.exists() and meta_path.exists():
        return None  # existing install: never touch the active model.
    src = Path(bundled) if bundled is not None else find_bundled_baseline()
    if src is None:
        return None
    manifest = validate_baseline_dir(src)
    recovery = baseline_recovery_dir(base)
    for name in BASELINE_FILENAMES:
        shutil.copy2(src / name, recovery / name)
    shutil.copy2(src / MANIFEST_FILENAME, recovery / MANIFEST_FILENAME)
    # Activate: copy into legacy flat active paths + profile.
    shutil.copy2(recovery / "model.joblib", model_path)
    shutil.copy2(recovery / "metadata.json", meta_path)
    shutil.copy2(recovery / "training_rows.jsonl", dataset_path)
    shutil.copy2(recovery / "timetable_learning_profile.json",
                 pattern_store.profile_path(base))
    # Prove the seeded model loads before reporting success.
    model_store.load_model(base)
    pattern_store.load_profile(base)
    try:
        from app.services.local_agent import model_versions
        model_versions.snapshot_version(base, label="baseline-seed")
    except Exception:
        pass
    write_seed_info(base, manifest)
    info = dict(manifest)
    info["seeded"] = True
    return info


SEED_INFO_FILENAME = "seed_info.json"


def seed_info_path(data_dir: Optional[Path] = None) -> Path:
    from app.database import get_data_dir
    from app.services.local_agent import model_store
    base = Path(data_dir) if data_dir is not None else get_data_dir()
    return model_store.model_dir(base) / SEED_INFO_FILENAME


def write_seed_info(data_dir: Optional[Path] = None,
                    manifest: Optional[Dict[str, Any]] = None) -> Path:
    """Record that the active model came from the bundled baseline."""
    from app.services.local_agent import model_store
    path = seed_info_path(data_dir)
    payload = {
        "seeded_from_baseline": True,
        "baseline_kind": (manifest or {}).get("baseline_kind", "unknown"),
        "baseline_trained_at": (manifest or {}).get("trained_at", ""),
        "baseline_lectures": (manifest or {}).get("lectures", 0),
        "seeded_at": model_store._utcnow(),
    }
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1)
    os.replace(tmp, path)
    return path


def clear_seed_info(data_dir: Optional[Path] = None) -> bool:
    """Mark the active model as locally trained (no longer pristine baseline)."""
    path = seed_info_path(data_dir)
    try:
        if path.exists():
            path.unlink()
            return True
        return False
    except OSError:
        return False


def active_origin(data_dir: Optional[Path] = None) -> Dict[str, Any]:
    """Where the active model came from: bundled baseline vs local training."""
    path = seed_info_path(data_dir)
    if path.is_file():
        try:
            info = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            info = {}
        if info.get("seeded_from_baseline"):
            kind = str(info.get("baseline_kind", "unknown"))
            if kind == "production":
                return {"origin": "bundled-production-baseline", "info": info}
            if kind == "sample":
                return {"origin": "bundled-sample-baseline", "info": info}
            return {"origin": "bundled-baseline", "info": info}
    return {"origin": "local", "info": {}}
