"""Local model persistence: model.joblib + metadata.json + training rows.

Everything lives under <app-data>/timetable_agent_model/ — one
installation owns exactly its own model. Writes are atomic (tmp file +
os.replace); a failed training never touches the working model, and a
corrupt store is quarantined aside, never silently kept.
"""
import datetime
import json
import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.database import get_data_dir
from app.services.local_agent.schemas import LearningError
from app.services.local_agent.trainable_model import MODEL_VERSION, predict_scores, train_model
from app.services.local_agent.training_dataset import (
    FEATURE_SCHEMA_VERSION, FEATURES_V1, build_dataset,
)

MODEL_DIRNAME = "timetable_agent_model"
MODEL_FILENAME = "model.joblib"
METADATA_FILENAME = "metadata.json"
DATASET_FILENAME = "training_rows.jsonl"


def model_dir(data_dir: Optional[Path] = None) -> Path:
    base = Path(data_dir) if data_dir is not None else get_data_dir()
    path = base / MODEL_DIRNAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def _paths(data_dir: Optional[Path] = None):
    root = model_dir(data_dir)
    return (root / MODEL_FILENAME, root / METADATA_FILENAME, root / DATASET_FILENAME)


def _utcnow() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def _load_dataset_rows(data_dir: Optional[Path] = None) -> List[dict]:
    """Stored training rows (the dataset model.joblib was trained on)."""
    _, _, dataset_path = _paths(data_dir)
    rows = []
    if dataset_path.exists():
        try:
            with open(dataset_path, "r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if line:
                        rows.append(json.loads(line))
        except (OSError, ValueError) as e:
            raise LearningError(f"Stored training data is unreadable: {e}")
    return rows


def dataset_rows(data_dir: Optional[Path] = None) -> List[dict]:
    """Public accessor for the stored training rows (profile rebuilds)."""
    return _load_dataset_rows(data_dir)


def _atomic_write_json(path: Path, payload: dict):
    tmp = path.with_suffix(path.suffix + ".tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=1)
        os.replace(tmp, path)
    except OSError as e:
        try:
            if tmp.exists():
                tmp.unlink()
        except OSError:
            pass
        raise LearningError(f"Cannot write '{path}': {e}")


def _atomic_write_joblib(path: Path, model):
    import joblib
    tmp = path.with_suffix(path.suffix + ".tmp")
    try:
        joblib.dump(model, tmp)
        os.replace(tmp, path)
    except Exception as e:
        try:
            if tmp.exists():
                tmp.unlink()
        except OSError:
            pass
        raise LearningError(f"Cannot persist trained model: {e}")


def _restore_backups(backups: Dict[Path, Path], tmps) -> None:
    """Remove staged tmps and put .bak files back over live files."""
    for tmp in tmps:
        try:
            if tmp.exists():
                tmp.unlink()
        except OSError:
            pass
    for live, bak in backups.items():
        try:
            if bak.exists():
                os.replace(bak, live)
        except OSError:
            pass


def train_from_rows(rows: List[dict], source_label: str = "",
                    data_dir: Optional[Path] = None,
                    replace: bool = False) -> Dict[str, Any]:
    """Train (or incrementally retrain) from normalized row dicts.

    replace=False appends to the stored local dataset first (incremental);
    replace=True starts from only the given rows. The previous working
    model is replaced atomically and only after the new one validates.
    Returns a training report dict.
    """
    stored = [] if replace else _load_dataset_rows(data_dir)
    combined = stored + [dict(r) for r in rows]
    if not combined:
        raise LearningError("No training rows supplied.")
    from app.services.local_agent.schemas import LectureRow
    from app.utils.helpers import time_to_minutes
    lecture_rows = []
    slot_pairs = set()
    for raw in combined:
        try:
            lecture_rows.append(LectureRow(
                code=str(raw.get("code", "")), name=str(raw.get("name", "")),
                type=str(raw.get("type", "Theory") or "Theory"),
                duration=int(raw.get("duration", 60) or 60),
                day=str(raw.get("day", "")), start=str(raw.get("start", "")),
                end=str(raw.get("end", "")), teacher=str(raw.get("teacher", "")),
                room=str(raw.get("room", ""))))
            start, end = time_to_minutes(str(raw.get("start", ""))), time_to_minutes(
                str(raw.get("end", "")))
            if end > start:
                slot_pairs.add((start, end))
        except (TypeError, ValueError, AttributeError):
            continue
    # Slot grid from observed times (not one giant block): negatives then
    # genuinely span mornings, afternoons and gaps.
    X, y, meta = build_dataset(lecture_rows, slots=sorted(slot_pairs) or None)
    model, metrics = train_model(X, y)
    model_path, meta_path, dataset_path = _paths(data_dir)
    report = {
        "model_version": MODEL_VERSION,
        "feature_schema": FEATURE_SCHEMA_VERSION,
        "features": list(FEATURES_V1),
        "trained_at": _utcnow(),
        "sources": sorted({str(r.get("source", source_label or "unknown")) for r in combined}),
        "lectures": len(combined),
        "files": meta.get("files", 1),
        **metrics,
    }
    # Truly atomic replacement: stage all three files to tmp names, back up
    # the live files, then replace all three. Any failure restores the
    # backups, so a crash can never leave new-model/old-dataset,
    # new-metadata/old-model, partial jsonl or corrupt joblib behind.
    # ponytail: group-rename via backups (not a real FS transaction);
    # upgrade path is a write-ahead journal if cross-crash guarantees harden.
    model_tmp = model_path.with_name(model_path.name + ".tmp")
    meta_tmp = meta_path.with_name(meta_path.name + ".tmp")
    dataset_tmp = dataset_path.with_name(dataset_path.name + ".tmp")
    backups: Dict[Path, Path] = {}
    try:
        for live in (model_path, meta_path, dataset_path):
            if live.exists():
                bak = live.with_name(live.name + ".bak")
                shutil.copy2(live, bak)
                backups[live] = bak
        try:
            import joblib
            joblib.dump(model, model_tmp)
        except Exception as e:
            raise LearningError(f"Cannot persist trained model: {e}")
        try:
            with open(meta_tmp, "w", encoding="utf-8") as fh:
                json.dump(report, fh, indent=1)
        except OSError as e:
            raise LearningError(f"Cannot write '{meta_path}': {e}")
        try:
            with open(dataset_tmp, "w", encoding="utf-8") as fh:
                for row in combined:
                    fh.write(json.dumps(row) + "\n")
        except OSError as e:
            raise LearningError(f"Cannot write '{dataset_path}': {e}")
        os.replace(model_tmp, model_path)
        os.replace(meta_tmp, meta_path)
        os.replace(dataset_tmp, dataset_path)
    except LearningError:
        _restore_backups(backups, (model_tmp, meta_tmp, dataset_tmp))
        raise
    except Exception as e:
        _restore_backups(backups, (model_tmp, meta_tmp, dataset_tmp))
        raise LearningError(f"Training failed before anything was replaced: {e}")
    for bak in backups.values():
        try:
            if bak.exists():
                bak.unlink()
        except OSError:
            pass
    try:
        _check_consistent(data_dir)
    except LearningError:
        _restore_backups(backups, ())
        raise
    report["model_path"] = str(model_path)
    return report


def _count_dataset_lines(data_dir: Optional[Path] = None) -> int:
    _, _, dataset_path = _paths(data_dir)
    try:
        with open(dataset_path, "r", encoding="utf-8") as fh:
            return sum(1 for line in fh if line.strip())
    except OSError:
        return 0


def _check_consistent(data_dir: Optional[Path] = None):
    """Metadata lecture count must match stored dataset rows.

    Raises LearningError (and quarantines) when a previous crash left a
    mixed state, so the app never trains-or-generates from mismatched data.
    """
    _, meta_path, _ = _paths(data_dir)
    try:
        with open(meta_path, "r", encoding="utf-8") as fh:
            metadata = json.load(fh)
    except (OSError, ValueError):
        return
    if not isinstance(metadata, dict):
        return
    expected = metadata.get("lectures")
    if expected is None:
        return
    actual = _count_dataset_lines(data_dir)
    if actual != expected:
        model_path, _, dataset_path = _paths(data_dir)
        _quarantine(model_path, meta_path, dataset_path)
        raise LearningError(
            f"Training store is inconsistent (metadata says {expected} "
            f"lectures, dataset has {actual} rows). Files were moved aside; "
            "train the agent again.")


def load_model(data_dir: Optional[Path] = None):
    """Load (model, metadata). Corrupt stores are quarantined, never kept."""
    model_path, meta_path, _ = _paths(data_dir)
    if not model_path.exists() or not meta_path.exists():
        raise LearningError(
            "No trained timetable model yet. Train the agent on previous "
            "timetable data first.")
    try:
        with open(meta_path, "r", encoding="utf-8") as fh:
            metadata = json.load(fh)
    except (OSError, ValueError):
        metadata = None
    try:
        import joblib
        model = joblib.load(model_path)
    except Exception:
        model = None
    if (model is None or not isinstance(metadata, dict)
            or metadata.get("model_version") != MODEL_VERSION
            or metadata.get("feature_schema") != FEATURE_SCHEMA_VERSION):
        _quarantine(model_path, meta_path)
        raise LearningError(
            "Stored timetable model is corrupted or from another version. "
            "It was moved aside; train the agent again.")
    _check_consistent(data_dir)
    return model, metadata


def _quarantine(*paths: Path):
    stamp = _utcnow().replace(":", "-")
    for path in paths:
        try:
            if path.exists():
                path.rename(path.with_name(f"{path.stem}.corrupt-{stamp}{path.suffix}"))
        except OSError:
            pass


def model_status(data_dir: Optional[Path] = None) -> Dict[str, Any]:
    """Status dict; trained=False when nothing usable is stored."""
    model_path, meta_path, dataset_path = _paths(data_dir)
    rows = 0
    if dataset_path.exists():
        try:
            with open(dataset_path, "r", encoding="utf-8") as fh:
                rows = sum(1 for line in fh if line.strip())
        except OSError:
            rows = 0
    if not model_path.exists() or not meta_path.exists():
        return {"trained": False, "model_path": str(model_path),
                "stored_rows": rows}
    try:
        with open(meta_path, "r", encoding="utf-8") as fh:
            metadata = json.load(fh)
    except (OSError, ValueError):
        return {"trained": False, "model_path": str(model_path),
                "stored_rows": rows, "error": "unreadable metadata"}
    if isinstance(metadata, dict) and metadata.get("lectures") is not None \
            and metadata.get("lectures") != rows:
        return {"trained": False, "model_path": str(model_path),
                "stored_rows": rows,
                "error": "inconsistent store (metadata/dataset mismatch)"}
    return {"trained": True, "model_path": str(model_path),
            "stored_rows": rows, **metadata}


def clear_model(data_dir: Optional[Path] = None) -> bool:
    """Remove model, metadata and stored rows. Returns True if removed."""
    model_path, meta_path, dataset_path = _paths(data_dir)
    removed = False
    for path in (model_path, meta_path, dataset_path):
        try:
            if path.exists():
                path.unlink()
                removed = True
        except OSError as e:
            raise LearningError(f"Cannot clear trained model: {e}")
    return removed


def score_candidates(model, feature_rows: List[List[float]]) -> List[float]:
    """Bounded [0, 1] suitability scores for candidate feature rows."""
    if not feature_rows:
        return []
    return predict_scores(model, feature_rows)
