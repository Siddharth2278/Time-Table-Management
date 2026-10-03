"""Internal network policy for the desktop application.

Single rule: local-agent traffic may only ever address this machine.
Allowed: 127.0.0.1, the 127.0.0.0/8 loopback range, ::1, and the name
"localhost". Everything else — LAN IPs, public IPs, hostnames — is
rejected. There is no telemetry, no update checker and no cloud client
anywhere else in app/; the only HTTP code in the project is the
localhost Ollama client, which enforces this policy at construction.
"""
import ipaddress
from typing import Tuple
from urllib.parse import urlparse


def endpoint_host(endpoint: str) -> str:
    """Lowercased hostname of a URL, "" when unparseable."""
    try:
        return (urlparse(endpoint).hostname or "").strip().lower()
    except Exception:
        return ""


def is_local_host(host: str) -> bool:
    """True only for loopback names/addresses (this PC)."""
    candidate = (host or "").strip().lower()
    if candidate in ("localhost",):
        return True
    try:
        return ipaddress.ip_address(candidate).is_loopback
    except ValueError:
        return False


def check_local_endpoint(endpoint: str) -> Tuple[bool, str]:
    """Return (allowed, host). Never raises."""
    host = endpoint_host(endpoint)
    if not host:
        return False, host
    return is_local_host(host), host


def require_local_endpoint(endpoint: str, what: str = "endpoint"):
    """Raise ValueError for non-local endpoints."""
    allowed, host = check_local_endpoint(endpoint)
    if not allowed:
        raise ValueError(
            f"Refusing non-local {what} '{endpoint}'. "
            "Local communication is restricted to this PC "
            "(127.0.0.1, localhost, or loopback IPv4/IPv6).")
