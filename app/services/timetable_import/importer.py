"""High-level import pipeline: files -> approved training dataset.

``TimetableImporter.import_file`` routes by extension; ``analyze_files``
collects per-file reports plus errors; ``approved_dicts`` converts only
approved records into the existing ML pipeline's dict shape.
"""
from pathlib import Path
from typing import Any, Dict, List

from app.services.timetable_import import preview as _preview
from app.services.timetable_import import validator as _validator
from app.services.timetable_import.models import FileExtraction, TimetableRecord
from app.services.timetable_import.registry import (
    SUPPORTED_EXTENSIONS, analyze_files, import_file,
)


class TimetableImporter:
    """Registry/factory entry point (easy to extend with new formats)."""

    SUPPORTED_EXTENSIONS = SUPPORTED_EXTENSIONS

    @staticmethod
    def import_file(path: str) -> FileExtraction:
        return import_file(path)

    @staticmethod
    def analyze_files(paths: List[str]) -> Dict[str, object]:
        return analyze_files(paths)

    @staticmethod
    def approved_dicts(extractions: List[FileExtraction]):
        """Only approved records -> lecture dicts + (approved, rejected)."""
        records: List[TimetableRecord] = []
        for extraction in extractions:
            records.extend(extraction.records)
        approved, rejected = _validator.validate_records(records)
        return _preview.records_to_lecture_dicts(approved), approved, rejected

    @staticmethod
    def save_approved(extractions: List[FileExtraction], data_dir=None):
        """Validate + stage approved rows in per-PC APPDATA. Returns path info."""
        records = []
        for extraction in extractions:
            records.extend(extraction.records)
        path, approved_count, rejected_count = _preview.save_approved_jsonl(
            records, data_dir)
        return {"path": str(path), "approved": approved_count,
                "rejected": rejected_count}

    @staticmethod
    def baseline_source_label(extractions: List[FileExtraction]) -> str:
        """Sanitized source label: basenames only, never absolute paths."""
        names = []
        for extraction in extractions:
            name = Path(extraction.file).name
            if name and name not in names:
                names.append(name)
        return ", ".join(names)
