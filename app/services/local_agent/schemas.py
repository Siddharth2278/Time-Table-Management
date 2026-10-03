"""Shared schemas for the local timetable agent.

Covers Phase 1 (learning) and Phase 2 (local-model planning + validated
generation). Deterministic parts stay deterministic; the model only
ever contributes preference guidance, never placements.
"""
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List

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


@dataclass
class PlanPlacement:
    """One model-suggested preference (NOT a placement decision)."""
    subject_id: int = 0
    day: str = ""
    start_time: str = ""
    rank: int = 0

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class GenerationResult:
    """Outcome of a validated dry run (Phase 2)."""
    accepted: List[dict] = field(default_factory=list)
    rejected: List[dict] = field(default_factory=list)
    unplaced: List[dict] = field(default_factory=list)
    hard_conflicts: int = 0
    structural_similarity: float = 0.0
    profile_info: Dict[str, Any] = field(default_factory=dict)
    stats: Dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "accepted": len(self.accepted),
            "unplaced": len(self.unplaced),
            "hard_conflicts": self.hard_conflicts,
            "structural_similarity": round(self.structural_similarity, 2),
            "profile": self.profile_info,
            "rejected": self.rejected,
            "statistics": self.stats,
        }


def blank_profile(source_label: str = "") -> Dict[str, Any]:
    return {
        "version": PROFILE_VERSION,
        "sources": [source_label] if source_label else [],
        "total_lectures": 0,
        "subjects": [],
        "roles": {},
        "patterns": {},
    }
