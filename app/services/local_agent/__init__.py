"""Local timetable agent package (Phase 1: learning only, fully offline)."""
from app.services.local_agent.agent import TimetableAgent
from app.services.local_agent.model_client import DEFAULT_ENDPOINT, OllamaClient
from app.services.local_agent.pattern_store import (
    clear_profile, load_profile, save_profile, update_profile,
)
from app.services.local_agent.schemas import (
    PROFILE_FILENAME, PROFILE_VERSION, LearningError,
)
from app.services.local_agent.timetable_learner import learn, load_rows

__all__ = [
    "DEFAULT_ENDPOINT", "LearningError", "OllamaClient", "PROFILE_FILENAME",
    "PROFILE_VERSION", "TimetableAgent", "clear_profile", "learn",
    "load_profile", "load_rows", "save_profile", "update_profile",
]
