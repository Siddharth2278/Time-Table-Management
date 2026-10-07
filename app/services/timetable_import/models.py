"""Canonical timetable records: one representation for every input format.

Extractors never feed pixels or raw cells to the ML pipeline. They produce
:class:`TimetableRecord` rows; only approved rows are converted into the
existing ``LectureRow`` dicts consumed by ``training_dataset``.
"""
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List


@dataclass
class TimetableRecord:
    """One normalized lecture extracted from any supported file."""
    day: str = ""
    start: str = ""
    end: str = ""
    subject: str = ""
    teacher: str = ""
    room: str = ""
    semester: str = ""
    lecture_type: str = "Theory"
    is_lab: bool = False
    source_file: str = ""
    source_page: int = 0
    source_row: int = -1
    source_col: int = -1
    confidence: float = 1.0
    warnings: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FileExtraction:
    """Result of importing one file: records + human-readable report."""
    file: str = ""
    file_type: str = ""
    method: str = ""
    records: List[TimetableRecord] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    pages: int = 1

    @property
    def lectures(self) -> int:
        return len(self.records)

    def confidence_summary(self) -> Dict[str, int]:
        high = medium = low = 0
        for record in self.records:
            if record.confidence >= 0.8:
                high += 1
            elif record.confidence >= 0.5:
                medium += 1
            else:
                low += 1
        return {"high": high, "medium": medium, "low": low}

    def as_report(self) -> Dict[str, Any]:
        return {
            "file": self.file,
            "type": self.file_type,
            "method": self.method,
            "pages": self.pages,
            "lectures": self.lectures,
            **self.confidence_summary(),
            "warnings": list(self.warnings),
        }
