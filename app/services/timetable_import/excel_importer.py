"""Excel extractor: .xlsx/.xlsm (openpyxl) and legacy .xls (xlrd).

Merged cells are unfolded to their top-left value; empty cells are skipped;
repeated header rows are ignored. Grids and row layouts share the same
normalizer as CSV.
"""
from typing import List

from app.services.timetable_import.exceptions import TimetableImportError
from app.services.timetable_import.models import FileExtraction
from app.services.timetable_import import table_normalizer as norm


def _grid_openpyxl(path: str) -> List[List[str]]:
    try:
        from openpyxl import load_workbook
    except ImportError:
        raise TimetableImportError("Excel support needs the openpyxl package.")
    try:
        workbook = load_workbook(path, read_only=True, data_only=True)
        sheet = workbook.active
        grid = [[("" if value is None else str(value))
                 for value in row] for row in sheet.iter_rows(values_only=True)]
        # Unfold merged cells to their top-left value.
        try:
            for merged in sheet.merged_cells.ranges:
                top = grid[merged.min_row - 1][merged.min_col - 1]
                for r in range(merged.min_row - 1, merged.max_row):
                    for c in range(merged.min_col - 1, merged.max_col):
                        if not (grid[r][c] or "").strip():
                            grid[r][c] = top
        except (AttributeError, IndexError):
            pass
        workbook.close()
        return grid
    except TimetableImportError:
        raise
    except Exception as e:
        raise TimetableImportError(f"Could not read this Excel file: {e}")


def _grid_xlrd(path: str) -> List[List[str]]:
    try:
        import xlrd
    except ImportError:
        raise TimetableImportError(
            "Legacy .xls support needs the xlrd package.")
    try:
        book = xlrd.open_workbook(path)
        sheet = book.sheet_by_index(0)
        grid = [[("" if value is None else str(value)).strip()
                 for value in sheet.row_values(r)]
                for r in range(sheet.nrows)]
        # Unfold merged cells.
        for r1, r2, c1, c2 in sheet.merged_cells:
            top = grid[r1][c1] if r1 < len(grid) and c1 < len(grid[r1]) else ""
            for r in range(r1, r2):
                for c in range(c1, c2):
                    if r < len(grid) and c < len(grid[r]) and not grid[r][c].strip():
                        grid[r][c] = top
        return grid
    except TimetableImportError:
        raise
    except Exception as e:
        raise TimetableImportError(f"Could not read this Excel file: {e}")


def extract(path: str, label: str) -> FileExtraction:
    suffix = "." + path.lower().rsplit(".", 1)[-1]
    if suffix == ".xls":
        grid = _grid_xlrd(path)
    else:
        grid = _grid_openpyxl(path)
    grid = [row for row in grid if any((cell or "").strip() for cell in row)]
    if not grid:
        raise TimetableImportError(f"No timetable data was detected in '{label}'.")
    # Drop repeated header rows (a header-like row appearing again later).
    headers = [(cell or "").strip() for cell in grid[0]]
    grid = [grid[0]] + [row for row in grid[1:]
                        if [(c or "").strip() for c in row] != headers]
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
    return FileExtraction(file=label, file_type=suffix, method="excel",
                          records=records, warnings=warnings)
