"""Ollama integration through localhost only. No cloud, no API keys.

- Endpoint configurable, default http://127.0.0.1:11434
  (override with the LOCAL_AGENT_OLLAMA_URL environment variable).
- Default model configurable with LOCAL_AGENT_MODEL (default "llama3.1").
- Phase 1 uses this client for availability checks; generation arrives
  in Phase 2. All failures raise LearningError with actionable text.
- Stdlib HTTP only (urllib): no new dependencies.
"""
import json
import os
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

from app.services.local_agent.netpolicy import require_local_endpoint
from app.services.local_agent.schemas import LearningError

DEFAULT_ENDPOINT = "http://127.0.0.1:11434"
DEFAULT_MODEL = "llama3.1"


def _ensure_local_endpoint(endpoint: str):
    """Reject anything that is not this machine. No silent remote hosts."""
    try:
        require_local_endpoint(endpoint, "Ollama endpoint")
    except ValueError as e:
        raise LearningError(
            str(e) + " The local agent only talks to this PC "
            "(http://127.0.0.1:11434 or http://localhost:11434).")


class OllamaClient:
    """Thin localhost Ollama client (chat API compatible)."""

    def __init__(self, endpoint: Optional[str] = None,
                 model: Optional[str] = None, timeout: int = 10):
        resolved = (endpoint or os.environ.get("LOCAL_AGENT_OLLAMA_URL")
                    or DEFAULT_ENDPOINT).rstrip("/")
        _ensure_local_endpoint(resolved)
        self.endpoint = resolved
        self.model = model or os.environ.get("LOCAL_AGENT_MODEL") or DEFAULT_MODEL
        self.timeout = timeout

    def _get(self, path: str) -> Any:
        request = urllib.request.Request(
            self.endpoint + path, method="GET",
            headers={"Accept": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as e:
            raise LearningError(
                f"Cannot reach Ollama at {self.endpoint} ({e}). "
                "Start it with `ollama serve` on this PC.")

    def _post(self, path: str, payload: dict) -> Any:
        request = urllib.request.Request(
            self.endpoint + path,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST")
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                raise LearningError(
                    f"Ollama endpoint {self.endpoint}{path} not found. "
                    "Check LOCAL_AGENT_OLLAMA_URL.")
            raise LearningError(f"Ollama request failed (HTTP {e.code}).")
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            raise LearningError(
                f"Cannot reach Ollama at {self.endpoint} ({e}). "
                "Start it with `ollama serve` on this PC.")
        except ValueError as e:
            raise LearningError(f"Ollama returned invalid data: {e}")

    def is_running(self) -> bool:
        """True when Ollama answers on localhost. Never raises."""
        try:
            self._get("/api/tags")
            return True
        except LearningError:
            return False

    def models(self) -> List[str]:
        """Names of locally pulled models, [] when unreachable."""
        try:
            data = self._get("/api/tags")
        except LearningError:
            return []
        names = []
        for item in data.get("models", []) if isinstance(data, dict) else []:
            name = item.get("name", "") if isinstance(item, dict) else ""
            if name:
                names.append(name)
        return names

    def is_model_available(self, model: Optional[str] = None) -> bool:
        wanted = (model or self.model).split(":")[0]
        return any(wanted == name.split(":")[0] for name in self.models())

    def ensure_ready(self, model: Optional[str] = None) -> str:
        """Raise LearningError unless Ollama runs and the model is pulled."""
        if not self.is_running():
            raise LearningError(
                f"Ollama is not running at {self.endpoint}. "
                "Install Ollama on this PC and start it with `ollama serve`.")
        wanted = model or self.model
        if not self.is_model_available(wanted):
            raise LearningError(
                f"Model '{wanted}' is not available locally. "
                f"Pull it once with `ollama pull {wanted}`, then retry. "
                "No internet account or API key is needed.")
        return wanted

    def generate(self, prompt: str, model: Optional[str] = None,
                 options: Optional[Dict[str, Any]] = None) -> str:
        """One non-streaming completion (reserved for Phase 2 generation)."""
        active = self.ensure_ready(model)
        data = self._post("/api/generate", {
            "model": active,
            "prompt": prompt,
            "stream": False,
            "options": options or {},
        })
        if not isinstance(data, dict) or not str(data.get("response", "")):
            raise LearningError("Ollama returned an empty response.")
        return str(data["response"])
