"""Shared schemas for the local timetable agent (Phase 1: learning only)."""
from dataclasses import asdict, dataclass
from typing import Any, Dict

PROFILE_VERSION = 1
PROFILE_FILENAME = "timetable_learning_profile.json"


class LearningError(Exception):
    """User-safe failure: invalid file, insufficient data, Ollama down, etc."""


@dataclass
class LectureRow:
    """One normalized lecture row from CSV / XLSX / JSON."""
    code: str = ""
    name: str = ""
    type: str = "Theory"
    duration: int = 60
    day: str = ""
    start: str = ""
    end: str = ""
    teacher: str = ""
    room: str = ""

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class LearningSummary:
    """Small human-readable result of analyze_reference_timetable()."""
    file: str = ""
    lectures: int = 0
    subjects: int = 0
    roles: int = 0
    skipped_rows: int = 0

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


def blank_profile(source_label: str = "") -> Dict[str, Any]:
    return {
        "version": PROFILE_VERSION,
        "sources": [source_label] if source_label else [],
        "total_lectures": 0,
        "subjects": [],
        "roles": {},
        "patterns": {},
    }
