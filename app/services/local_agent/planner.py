"""Local-model planning: learned profile + requirements -> strict plan JSON.

The model produces preference guidance ONLY (ranked day/time wishes per
subject). It never places, never validates, never writes. Everything it
returns is strictly validated; unknown IDs, bad days/times, duplicates
and malformed output are rejected before the solver ever sees them.
"""
import json
import re
from typing import Any, Dict, List, Tuple

from app.services.local_agent.model_client import OllamaClient
from app.services.local_agent.schemas import LearningError, PlanPlacement
from app.utils.helpers import time_to_minutes

PLAN_SCHEMA_HINT = """Return STRICT JSON only, no prose:
{"placements": [{"subject_id": int, "day": "DayName", "start_time": "HH:MM", "rank": int}],
 "notes": "short string"}"""


def build_plan_prompt(requirements: Dict[str, Any], learned: Dict[str, Any],
                      previous_failures: List[str] | None = None) -> str:
    """Prompt carrying profile patterns + current requirements + valid values."""
    patterns = learned.get("patterns", {}) or {}
    roles = learned.get("roles", {}) or {}
    role_lines = []
    for key in sorted(roles):
        role = roles[key]
        role_lines.append(
            f"- {key}: preferred days {', '.join(role.get('preferred_days', [])) or '-'}; "
            f"preferred times {', '.join(role.get('preferred_times', [])) or '-'}; "
            f"morning share {role.get('morning_share')}; "
            f"adjacent-pair rate {role.get('adjacent_pair_rate')}.")
    subject_lines = []
    for item in requirements.get("subjects", []):
        subject_lines.append(
            f"- id {item['id']} ({item['code']}): {item['type']} "
            f"{item['duration']}min, {item['required']}/week")
    day_names = [d["name"] for d in requirements.get("days", [])]
    slot_starts = sorted({s["start"] for s in requirements.get("slots", [])
                          if not s.get("break")})
    prompt = (
        "You are a college timetable planning assistant. Suggest preferred "
        "day/time placements using the college's historical patterns below. "
        "Rules: use ONLY the listed day names and slot start times; rank 1 "
        "is the strongest wish; cover each subject up to its weekly count; "
        "never invent subjects, days or times.\n\n"
        f"HISTORICAL PATTERNS (sources: {', '.join(learned.get('sources', [])) or 'n/a'}):\n"
        f"Preferred days: {', '.join(patterns.get('preferred_days', []))}\n"
        f"Preferred times: {', '.join(patterns.get('preferred_times', []))}\n"
        f"Morning share: {patterns.get('morning_share')}; "
        f"avg daily load: {patterns.get('average_daily_load')}.\n"
        + ("\n".join(role_lines) + "\n" if role_lines else "")
        + "\nCURRENT REQUIREMENTS:\n"
        + ("\n".join(subject_lines) + "\n" if subject_lines else "")
        + f"Valid days: {', '.join(day_names)}\n"
        + f"Valid slot starts: {', '.join(slot_starts)}\n")
    if previous_failures:
        prompt += ("\nPreviously rejected (do NOT repeat these exact "
                   "subject/day/start combinations):\n"
                   + "\n".join(previous_failures[:20]) + "\n")
    return prompt + "\n" + PLAN_SCHEMA_HINT


def request_plan(client: OllamaClient, model: str, prompt: str) -> str:
    """Ask the local model for a plan. Model/dial errors become LearningError."""
    active = client.ensure_ready(model)
    return client.generate(prompt, model=active,
                           options={"temperature": 0.2, "num_predict": 2000})


def _choices_text(raw: str) -> str:
    return raw if isinstance(raw, str) else ""


def parse_plan(text: str, requirements: Dict[str, Any]) -> Tuple[List[dict], List[str], str]:
    """Strictly validate a model plan.

    Returns (placements, dropped_notes, model_notes). Placements are
    [{subject_id, day, start_time, rank}]. Raises LearningError when
    nothing usable remains; individual bad rows are dropped with reasons.
    """
    text = _choices_text(text).strip()
    fence = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    if fence:
        text = fence.group(1)
    try:
        data = json.loads(text)
    except (ValueError, TypeError):
        raise LearningError("Model output was not valid JSON; nothing planned.")
    if not isinstance(data, dict) or not isinstance(data.get("placements"), list):
        raise LearningError("Model output missed the required 'placements' list.")
    valid_days = {d["name"] for d in requirements.get("days", [])}
    valid_starts = {s["start"] for s in requirements.get("slots", [])
                    if not s.get("break")}
    known_subjects = {item["id"] for item in requirements.get("subjects", [])}
    placements: List[dict] = []
    dropped: List[str] = []
    seen = set()
    for i, row in enumerate(data["placements"]):
        try:
            if not isinstance(row, dict):
                raise LearningError("row")
            sid = row.get("subject_id")
            if isinstance(sid, bool) or not isinstance(sid, int) or sid <= 0:
                raise LearningError("subject_id")
            if sid not in known_subjects:
                raise LearningError(f"unknown subject_id {sid}")
            day = str(row.get("day", "")).strip()
            if day not in valid_days:
                raise LearningError(f"unknown day '{day}'")
            start = str(row.get("start_time", "")).strip()
            if start not in valid_starts:
                raise LearningError(f"unknown start_time '{start}'")
            try:
                rank = int(row.get("rank", 0))
            except (TypeError, ValueError):
                raise LearningError("rank")
            if rank < 1:
                raise LearningError("rank")
            key = (sid, day, start)
            if key in seen:
                raise LearningError(f"duplicate {key}")
            seen.add(key)
            placements.append({"subject_id": sid, "day": day,
                               "start_time": start, "rank": rank})
        except LearningError as e:
            dropped.append(f"Row {i}: {e}")
    notes = data.get("notes", "")
    if not isinstance(notes, str):
        notes = ""
    if not placements:
        raise LearningError(
            "Model produced no usable placements (" +
            "; ".join(dropped[:3]) + "). Nothing planned.")
    return placements, dropped, notes


def plan_to_bias(placements: List[dict]) -> Dict[tuple, int]:
    """Convert validated placements to solver bias {(sid, day_name, start): rank}."""
    bias: Dict[tuple, int] = {}
    for item in placements:
        key = (item["subject_id"], item["day"], item["start_time"])
        rank = item["rank"]
        if key not in bias or rank < bias[key]:
            bias[key] = rank
    return bias
