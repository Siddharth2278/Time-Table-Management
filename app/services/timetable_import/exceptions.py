"""Timetable import errors (all user-displayable, never tracebacks)."""
from app.services.local_agent.schemas import LearningError


class TimetableImportError(LearningError):
    """Raised for unsupported/corrupt/unreadable timetable files."""
