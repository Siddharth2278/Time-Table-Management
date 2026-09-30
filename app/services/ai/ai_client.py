"""Online AI provider layer. No local models, no embedded inference.

- Works ONLY when internet is available (checked before every call).
- Provider is replaceable: OpenAI-compatible chat-completions by default,
  any compatible endpoint via configuration.
- API keys come from the environment (CTM_AI_API_KEY) or the secure
  local store — never hardcoded, never logged, never committed.
- Only stdlib (urllib/socket/json): no new dependencies.
"""
import json
import os
import socket
import ssl
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import Callable, Dict, Optional


class AIError(Exception):
    """User-safe AI failure (message is displayable, never a traceback)."""

    def __init__(self, message: str, kind: str = "api"):
        super().__init__(message)
        self.kind = kind


@dataclass
class AIConfig:
    provider: str = "openai-compatible"
    endpoint: str = ""
    model: str = ""
    api_key: str = ""
    timeout: int = 45
    # Test hook: replaces the HTTP call. Never used in production.
    post_impl: Optional[Callable[[str, dict, dict], dict]] = None

    @staticmethod
    def from_env() -> "AIConfig":
        return AIConfig(
            provider=os.environ.get("CTM_AI_PROVIDER", "openai-compatible"),
            endpoint=os.environ.get("CTM_AI_ENDPOINT", ""),
            model=os.environ.get("CTM_AI_MODEL", ""),
            api_key=os.environ.get("CTM_AI_API_KEY", ""),
            timeout=int(os.environ.get("CTM_AI_TIMEOUT", "45")),
        )


def stored_key_get() -> str:
    """API key from secure local store (env var wins, checked by caller)."""
    try:
        from PySide6.QtCore import QSettings
        return str(QSettings("CollegeTimetable", "Manager").value("ai/api_key", "") or "")
    except Exception:
        return ""


def stored_key_set(key: str):
    try:
        from PySide6.QtCore import QSettings
        QSettings("CollegeTimetable", "Manager").setValue("ai/api_key", key)
    except Exception:
        pass


def config_from_settings(session) -> AIConfig:
    """Build AIConfig: Setting table for provider/endpoint/model/flags,
    key from CTM_AI_API_KEY env first, then the secure local store."""
    def get(key, default=""):
        try:
            from app.models import Setting
            row = session.query(Setting).filter(Setting.key == key).first()
            return row.value if row else default
        except Exception:
            return default
    return AIConfig(
        provider=get("ai_provider", "openai-compatible"),
        endpoint=get("ai_endpoint", ""),
        model=get("ai_model", ""),
        api_key=os.environ.get("CTM_AI_API_KEY", "") or stored_key_get(),
    )


def reference_enabled(session) -> bool:
    try:
        from app.models import Setting
        row = session.query(Setting).filter(
            Setting.key == "ai_reference_enabled").first()
        return (row.value if row else "1") != "0"
    except Exception:
        return True


def _host_port(endpoint: str):
    try:
        from urllib.parse import urlparse
        parts = urlparse(endpoint)
        host = parts.hostname or ""
        port = parts.port or (443 if parts.scheme == "https" else 80)
        return host, port
    except Exception:
        return "", 0


def check_internet(endpoint: str, timeout: int = 4) -> bool:
    """True when the provider host is reachable. No data is exchanged."""
    host, port = _host_port(endpoint)
    if not host:
        return False
    try:
        socket.create_connection((host, port), timeout=timeout).close()
        return True
    except OSError:
        return False


def provider_status(config: AIConfig) -> Dict[str, str]:
    """Ready only with endpoint + key + reachable host. Never exposes the key."""
    if not (config.endpoint or "").strip() or not (config.model or "").strip():
        return {"state": "unconfigured",
                "message": "AI provider not configured. Set it in Settings."}
    if not (config.api_key or "").strip():
        return {"state": "unconfigured",
                "message": "API key missing. Set it in Settings or CTM_AI_API_KEY."}
    if not check_internet(config.endpoint):
        return {"state": "offline",
                "message": "Internet connection required."}
    return {"state": "ready", "message": "Connected."}


def post_chat(config: AIConfig, messages: list, temperature: float = 0.2) -> dict:
    """POST one chat-completions request, return the decoded JSON body."""
    if config.post_impl is not None:
        return config.post_impl(config.endpoint, config.model, messages)
    url = config.endpoint.rstrip("/") + "/chat/completions"
    body = {
        "model": config.model,
        "temperature": temperature,
        "response_format": {"type": "json_object"},
        "messages": messages,
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config.api_key}",
        },
        method="POST",
    )
    context = ssl.create_default_context()
    try:
        with urllib.request.urlopen(request, timeout=config.timeout, context=context) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            raise AIError("Invalid API key.", kind="auth")
        if e.code == 429:
            raise AIError("Rate limit reached. Try again later.", kind="rate")
        raise AIError(f"AI service unavailable (HTTP {e.code}).", kind="api")
    except urllib.error.URLError:
        raise AIError("Internet connection required.", kind="offline")
    except TimeoutError:
        raise AIError("AI request timed out.", kind="timeout")
    except (ValueError, OSError) as e:
        raise AIError(f"AI request failed: {e}", kind="api")
