"""Local timetable agent package (Phase 1 learning + Phase 2 generation).

Layers, kept distinct by design:
- LEARNING PROFILE: deterministic historical file analysis (timetable_learner).
- LOCAL AI: Ollama reasoning over the learned profile into preference
  guidance only (planner + model_client). Never places, never validates.
- SOLVER: existing intelligence optimizer + ConflictService (placement +
  validation). Never trusts model output.
- EDITOR: the existing timetable grid (human edits after Apply).
"""
from app.services.local_agent.agent import TimetableAgent
from app.services.local_agent.model_client import DEFAULT_ENDPOINT, OllamaClient
from app.services.local_agent.pattern_store import (
    clear_profile, load_profile, save_profile, update_profile,
)
from app.services.local_agent.planner import (
    build_plan_prompt, parse_plan, plan_to_bias, request_plan,
)
from app.services.local_agent.requirements import (
    collect_requirements, learned_to_reference, map_requirements_to_roles,
)
from app.services.local_agent.schemas import (
    PROFILE_FILENAME, PROFILE_VERSION, GenerationResult, LearningError,
    PlanPlacement,
)
from app.services.local_agent.timetable_learner import learn, load_rows

__all__ = [
    "DEFAULT_ENDPOINT", "GenerationResult", "LearningError", "OllamaClient",
    "PROFILE_FILENAME", "PROFILE_VERSION", "PlanPlacement", "TimetableAgent",
    "build_plan_prompt", "clear_profile", "collect_requirements", "learn",
    "learned_to_reference", "load_profile", "load_rows",
    "map_requirements_to_roles", "parse_plan", "plan_to_bias",
    "request_plan", "save_profile", "update_profile",
]
