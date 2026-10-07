"""Local timetable import package (multi-format, fully offline).

Supported inputs: .csv, .xlsx, .xls, .pdf, .jpg, .jpeg, .png, .webp, .bmp
(plus the learner's legacy .json, handled by the existing pipeline).

Flow: raw file -> format extractor -> normalized records -> validation ->
user preview/correction -> canonical training dataset -> existing ML
pipeline. Extractors never train; the model never sees pixels.
"""
from app.services.timetable_import.exceptions import TimetableImportError
from app.services.timetable_import.importer import (
    TimetableImporter, analyze_files, import_file,
)
from app.services.timetable_import.registry import SUPPORTED_EXTENSIONS
from app.services.timetable_import.models import FileExtraction, TimetableRecord
from app.services.timetable_import.preview import (
    records_to_lecture_dicts, save_approved_jsonl,
)
from app.services.timetable_import.validator import (
    split_approved, validate_records,
)

__all__ = [
    "SUPPORTED_EXTENSIONS", "FileExtraction", "TimetableImportError",
    "TimetableRecord", "analyze_files", "import_file",
    "records_to_lecture_dicts", "save_approved_jsonl", "split_approved",
    "validate_records",
]
