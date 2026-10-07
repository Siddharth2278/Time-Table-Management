"""Format registry: extension -> extractor. No network, no code execution."""
from pathlib import Path
from typing import Dict, List

from app.services.timetable_import.exceptions import TimetableImportError
from app.services.timetable_import.models import FileExtraction

SUPPORTED_EXTENSIONS = {
    ".csv", ".xlsx", ".xlsm", ".xltx", ".xltm", ".xls",
    ".pdf", ".jpg", ".jpeg", ".png", ".webp", ".bmp",
}

MAX_FILE_MB = 25
MAX_PDF_PAGES = 50
MAX_IMAGE_DIM = 8000


def _check_size(path: Path) -> None:
    try:
        size_mb = path.stat().st_size / (1024 * 1024)
    except OSError as e:
        raise TimetableImportError(f"Cannot read file '{path}': {e}")
    if size_mb > MAX_FILE_MB:
        raise TimetableImportError(
            f"File '{path.name}' is {size_mb:.1f} MB; "
            f"the limit is {MAX_FILE_MB} MB.")


def detect_type(path: str) -> str:
    """Lowercase extension ('' when none). Never raises."""
    name = str(path)
    return name.lower().rsplit(".", 1)[-1] if "." in name else ""


def import_file(path: str) -> FileExtraction:
    """Import one file into normalized records. Raises TimetableImportError."""
    from app.services.timetable_import import csv_importer, excel_importer
    from app.services.timetable_import import image_importer, pdf_importer
    src = Path(path)
    suffix = "." + detect_type(path)
    if suffix not in SUPPORTED_EXTENSIONS:
        raise TimetableImportError(
            f"This file type is not supported: '{suffix or '(none)'}'. "
            "Use .csv, .xlsx, .xls, .pdf, .jpg, .jpeg, .png, .webp or .bmp.")
    if not src.is_file():
        raise TimetableImportError(f"File not found: '{path}'.")
    _check_size(src)
    label = src.name
    if suffix == ".csv":
        return csv_importer.extract(str(src), label)
    if suffix in (".xlsx", ".xlsm", ".xltx", ".xltm", ".xls"):
        return excel_importer.extract(str(src), label)
    if suffix == ".pdf":
        return pdf_importer.extract(str(src), label)
    return image_importer.extract(str(src), label)


def analyze_files(paths: List[str]) -> Dict[str, object]:
    """Import many files; unusable files are reported, not fatal.

    Returns {"extractions": [...], "reports": [...], "errors": [...]},
    where errors are {"file": ..., "error": ...} dicts.
    """
    extractions: List[FileExtraction] = []
    errors: List[Dict[str, str]] = []
    for path in paths:
        try:
            extractions.append(import_file(str(path)))
        except TimetableImportError as e:
            errors.append({"file": str(path), "error": str(e)})
    return {"extractions": extractions,
            "reports": [e.as_report() for e in extractions],
            "errors": errors}
