"""Online AI timetable assistant (internet-only)."""
from app.services.ai.ai_client import AIConfig, AIError, check_internet, provider_status
from app.services.ai.prompt_builder import (
    build_messages, build_payload, build_reference_profile,
)
from app.services.ai.timetable_agent import (
    STAGES, apply_proposal, run as run_agent,
)
from app.services.ai.timetable_parser import extract_json, parse_proposal

__all__ = [
    "AIConfig", "AIError", "STAGES", "apply_proposal",
    "build_messages", "build_payload", "build_reference_profile",
    "check_internet", "extract_json", "parse_proposal",
    "provider_status", "run_agent",
]
