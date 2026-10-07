"""Preview helpers: approved records -> existing training pipeline.

Converts canonical records into the LectureRow-dict shape consumed by
``training_dataset.load_files_as_dicts`` and stages user-approved datasets
under the per-PC application data directory (never the repository).
"""
import datetime
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from app.services.timetable_import.models import TimetableRecord
from app.services.timetable_import.validator import validate_records

APPROVED_DIRNAME = "approved_imports"


def records_to_lecture_dicts(records: List[TimetableRecord]) -> List[Dict[str, Any]]:
    """Approved records -> LectureRow dicts (code/name/type/duration/...)."""
    out = []
    for record in records:
        from app.utils.helpers import time_to_minutes
        try:
            minutes = time_to_minutes(record.end) - time_to_minutes(record.start)
        except (ValueError, AttributeError, TypeError):
            continue
        subject = (record.subject or "").strip()
        if not subject:
            continue
        out.append({
            "code": subject, "name": subject,
            "type": (record.lecture_type or "Theory"),
            "duration": minutes,
            "day": record.day, "start": record.start, "end": record.end,
            "teacher": (record.teacher or "").strip(),
            "room": (record.room or "").strip(),
            "source": record.source_file or "import",
        })
    return out


def approved_staging_dir(data_dir=None) -> Path:
    from app.database import get_data_dir
    base = Path(data_dir) if data_dir is not None else get_data_dir()
    path = base / APPROVED_DIRNAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_approved_jsonl(records: List[TimetableRecord],
                        data_dir=None) -> Tuple[Path, int, int]:
    """Validate + persist approved rows as canonical JSONL in APPDATA.

    Returns (path, approved_count, rejected_count). Raises when nothing is
    approved: training must never run on rejected rows.
    """
    from app.services.local_agent.schemas import LearningError
    approved, rejected = validate_records(records)
    if not approved:
        raise LearningError(
            "No approved timetable records are available for training.")
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    path = approved_staging_dir(data_dir) / f"approved-{stamp}.jsonl"
    dicts = records_to_lecture_dicts(approved)
    if not dicts:
        raise LearningError(
            "No approved timetable records are available for training.")
    with open(path, "w", encoding="utf-8") as fh:
        for item in dicts:
            fh.write(json.dumps(item) + "\n")
    return path, len(dicts), len(rejected)
