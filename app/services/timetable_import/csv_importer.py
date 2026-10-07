"""CSV extractor: row layouts (A/C) and grid layouts (B/D)."""
import csv
from typing import List

from app.services.timetable_import.exceptions import TimetableImportError
from app.services.timetable_import.models import FileExtraction
from app.services.timetable_import import table_normalizer as norm


def _read_rows(path: str) -> List[List[str]]:
    try:
        with open(path, "r", encoding="utf-8-sig", newline="") as fh:
            return [row for row in csv.reader(fh)]
    except OSError as e:
        raise TimetableImportError(f"Cannot read timetable file '{path}': {e}")


def extract(path: str, label: str) -> FileExtraction:
    grid = _read_rows(path)
    grid = [row for row in grid if any((cell or "").strip() for cell in row)]
    if not grid:
        raise TimetableImportError(f"No timetable data was detected in '{label}'.")
    headers = [(cell or "").strip() for cell in grid[0]]
    if norm.looks_like_grid(headers):
        records, warnings = norm.grid_to_records(grid, label)
    else:
        dicts = [dict(zip(headers, [(cell or "") for cell in row]))
                 for row in grid[1:]]
        records, warnings = norm.row_dicts_to_records(dicts, label)
    if not records:
        raise TimetableImportError(
            f"No timetable data was detected in '{label}'. "
            + (" ".join(warnings) if warnings else ""))
    return FileExtraction(file=label, file_type=".csv", method="csv",
                          records=records, warnings=warnings)
