"""Local timetable agent package (learning + fitted model + generation).

Layers, kept distinct by design:
- LEARNING PROFILE: deterministic historical file analysis (timetable_learner).
- TRAINED MODEL: fitted sklearn classifier on structural features, stored
  locally per installation (trainable_model + model_store). Never sees names.
- LOCAL AI: Ollama reasoning over the learned profile into preference
  guidance only (planner + model_client). Never places, never validates.
- SOLVER: existing intelligence optimizer + ConflictService (placement +
  validation). Never trusts model output.
- EDITOR: the existing timetable grid (human edits after Apply).
"""
from app.services.local_agent.agent import TimetableAgent
from app.services.local_agent.model_client import DEFAULT_ENDPOINT, OllamaClient
from app.services.local_agent.model_store import (
    clear_model, dataset_rows, load_model, model_status,
)
from app.services.local_agent.baseline import (
    export_baseline, export_package, find_bundled_baseline, import_package,
    seed_active_from_baseline, validate_baseline_dir,
)
from app.services.local_agent.model_versions import (
    list_versions, rollback_to_version,
)
from app.services.local_agent.adaptive import (
    adaptive_config, adaptive_status, clear_feedback, maybe_retrain,
    pending_feedback, record_feedback, training_history,
)
from app.services.local_agent.netpolicy import (
    check_local_endpoint, endpoint_host, is_local_host,
)
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
    "adaptive_config", "adaptive_status", "build_plan_prompt",
    "check_local_endpoint", "clear_feedback", "clear_model", "clear_profile",
    "collect_requirements", "dataset_rows", "endpoint_host",
    "export_baseline", "export_package", "find_bundled_baseline",
    "import_package", "is_local_host",
    "learn", "learned_to_reference", "list_versions", "load_model",
    "load_profile", "load_rows", "map_requirements_to_roles",
    "maybe_retrain", "model_status", "parse_plan", "pending_feedback",
    "plan_to_bias", "record_feedback", "request_plan",
    "rollback_to_version", "save_profile", "seed_active_from_baseline",
    "training_history", "update_profile", "validate_baseline_dir",
]
