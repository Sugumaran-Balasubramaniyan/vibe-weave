#!/usr/bin/env python3
"""Safe, project-local bridge between Mistral Vibe hooks and Glass Box.

The program deliberately speaks only JSON on stdout because Vibe treats any
other stdout as a failed hook invocation.  Diagnostics stay on stderr.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass
from typing import Any, Callable, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlparse, urlunparse
from urllib.request import Request, urlopen


DEFAULT_EVENTS_URL = "http://127.0.0.1:8000/api/v1/vibe/events"
DEFAULT_TIMEOUT_SECONDS = 1.5
MAX_SUMMARY_CHARS = 800
MAX_REASON_CHARS = 600
MAX_IDENTIFIER_CHARS = 80
REDACTED = "[REDACTED]"
SECRET_KEY_PATTERN = re.compile(
    r"(api[_-]?key|authorization|cookie|credential|password|secret|token|private[_-]?key|bearer)",
    re.IGNORECASE,
)
SECRET_VALUE_PATTERN = re.compile(
    r"(?i)(\b(?:authorization|bearer|token|password|secret|api[_-]?key|credential)\b\s*(?:=|:|\s+)\s*)(?:bearer\s+)?([^\s,;]+)"
)


@dataclass(frozen=True)
class AdapterConfig:
    """Non-secret connection information for a single hook invocation."""

    events_url: str
    control_url_template: str
    token: str | None
    run_id: str | None
    timeout_seconds: float

    @classmethod
    def from_env(cls) -> "AdapterConfig":
        events_url = os.getenv("GLASSBOX_VIBE_EVENTS_URL", DEFAULT_EVENTS_URL).rstrip("/")
        template = os.getenv("GLASSBOX_VIBE_CONTROL_URL_TEMPLATE")
        if not template:
            template = _default_control_url(events_url)
        return cls(
            events_url=events_url,
            control_url_template=template,
            token=os.getenv("GLASSBOX_VIBE_TOKEN") or None,
            run_id=os.getenv("GLASSBOX_VIBE_RUN_ID") or None,
            timeout_seconds=_timeout_from_env(),
        )


RequestFn = Callable[..., dict[str, Any]]


def _default_control_url(events_url: str) -> str:
    marker = "/api/v1/vibe/events"
    if marker in events_url:
        return events_url.split(marker, 1)[0] + "/api/v1/runs/{run_id}/control"
    parsed = urlparse(events_url)
    return urlunparse((parsed.scheme, parsed.netloc, "/api/v1/runs/{run_id}/control", "", "", ""))


def _timeout_from_env() -> float:
    try:
        return max(0.1, min(float(os.getenv("GLASSBOX_VIBE_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS)), 10.0))
    except ValueError:
        return DEFAULT_TIMEOUT_SECONDS


def _redact_text(value: str, limit: int = MAX_SUMMARY_CHARS) -> str:
    value = SECRET_VALUE_PATTERN.sub(r"\1" + REDACTED, value)
    if len(value) > limit:
        return value[:limit] + "… [truncated]"
    return value


def _safe_identifier(value: Any, fallback: str) -> str:
    """Keep correlation fields useful without transmitting unbounded identifiers."""
    text = _redact_text(str(value or fallback), MAX_IDENTIFIER_CHARS)
    return text[:MAX_IDENTIFIER_CHARS] or fallback


def _redact(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): REDACTED if SECRET_KEY_PATTERN.search(str(key)) else _redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact(item) for item in value]
    if isinstance(value, tuple):
        return [_redact(item) for item in value]
    if isinstance(value, str):
        return _redact_text(value)
    return value


def _compact_summary(value: Any) -> str | None:
    if value is None:
        return None
    safe_value = _redact(value)
    if isinstance(safe_value, str):
        return safe_value
    try:
        return _redact_text(json.dumps(safe_value, sort_keys=True, ensure_ascii=False, separators=(",", ":")))
    except (TypeError, ValueError):
        return _redact_text(str(safe_value))


def _stable_fallback_id(invocation: Mapping[str, Any]) -> str:
    identity = {
        "session_id": _safe_identifier(invocation.get("session_id"), "unknown-session"),
        "tool_name": _safe_identifier(invocation.get("tool_name"), "unknown-tool"),
        "tool_input": _redact(invocation.get("tool_input") or {}),
    }
    encoded = json.dumps(identity, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:20]


def _correlation_id(invocation: Mapping[str, Any]) -> str:
    session_id = _safe_identifier(invocation.get("session_id"), "unknown-session")
    call_id = _safe_identifier(invocation.get("tool_call_id"), _stable_fallback_id(invocation))
    return f"{session_id}:{call_id}"


def _error_signature(error: Any) -> str | None:
    if not error:
        return None
    redacted = _compact_summary(error)
    if not redacted:
        return None
    normalized = re.sub(r"\s+", " ", redacted).strip()
    return normalized[:240]


def normalize_event(phase: str, invocation: Mapping[str, Any]) -> dict[str, Any]:
    """Convert Vibe's hook payload into a bounded, redacted Glass Box event."""

    phase = _canonical_phase(phase)
    correlation_id = _correlation_id(invocation)
    status = "pending"
    if phase == "post_tool":
        status = {
            "success": "ok",
            "failure": "error",
            "cancelled": "cancelled",
        }.get(str(invocation.get("tool_status") or "").lower(), "unknown")

    event: dict[str, Any] = {
        "schema_version": 1,
        "source": "mistral-vibe",
        "event_id": f"{correlation_id}:{phase}",
        "correlation_id": correlation_id,
        "phase": phase,
        "event_type": "tool.pre" if phase == "pre_tool" else "tool.post",
        "session_id": _safe_identifier(invocation.get("session_id"), "unknown-session"),
        "tool_name": _safe_identifier(invocation.get("tool_name"), "unknown-tool"),
        "tool_call_id": _safe_identifier(
            invocation.get("tool_call_id"), correlation_id.rsplit(":", 1)[-1]
        ),
        "input_summary": _compact_summary(invocation.get("tool_input")),
        "status": status,
    }
    if phase == "post_tool":
        output = invocation.get("tool_output_text")
        if output is None:
            output = invocation.get("tool_output")
        event.update(
            {
                "output_summary": _compact_summary(output),
                "error_signature": _error_signature(invocation.get("tool_error")),
                "duration_ms": invocation.get("duration_ms"),
            }
        )
    return event


def _canonical_phase(phase: str) -> str:
    aliases = {"before_tool": "pre_tool", "after_tool": "post_tool"}
    phase = aliases.get(phase, phase)
    if phase not in {"pre_tool", "post_tool"}:
        raise ValueError("phase must be pre_tool or post_tool")
    return phase


def request_json(
    method: str,
    url: str,
    payload: object | None,
    *,
    token: str | None,
    timeout_seconds: float,
) -> dict[str, Any]:
    """Issue one bounded JSON request without leaking transport errors to stdout."""

    headers = {"Accept": "application/json"}
    data: bytes | None = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    if token:
        headers["X-GlassBox-Token"] = token
    request = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=timeout_seconds) as response:  # nosec B310 - configured local service
            body = response.read(64 * 1024).decode("utf-8")
    except (HTTPError, URLError, OSError) as exc:
        raise RuntimeError(f"Glass Box request failed: {exc}") from exc
    if not body.strip():
        return {}
    decoded = json.loads(body)
    if not isinstance(decoded, dict):
        raise RuntimeError("Glass Box response must be a JSON object")
    return decoded


def _control_url(template: str, run_id: str, event: Mapping[str, Any]) -> str:
    url = template.format(run_id=quote(run_id, safe=""))
    query = urlencode({"session_id": event["session_id"], "tool_call_id": event["tool_call_id"]})
    return f"{url}{'&' if '?' in url else '?'}{query}"


def _deny_reason(control: Mapping[str, Any], action: str) -> str:
    instruction = control.get("instruction") or control.get("reason") or control.get("message")
    if instruction:
        return _redact_text(str(instruction), MAX_REASON_CHARS)
    if action in {"abort", "aborted"}:
        return "The operator stopped this Glass Box run. Do not execute another tool."
    return "Glass Box paused this run after detecting a repetitive or failing tool pattern. Wait for an operator override."


def handle_invocation(
    phase: str,
    invocation: Mapping[str, Any],
    config: AdapterConfig,
    *,
    request: RequestFn = request_json,
) -> dict[str, str]:
    """Report a Vibe hook event and return a Vibe structured hook response.

    Reporting/control transport errors intentionally allow the Vibe tool to run:
    hook configuration is observational by default. A positive backend brake or
    abort, however, is returned as a Vibe `deny` and therefore gates the tool.
    """

    phase = _canonical_phase(phase)
    event = normalize_event(phase, invocation)
    try:
        posted = request(
            "POST",
            config.events_url,
            event,
            token=config.token,
            timeout_seconds=config.timeout_seconds,
        )
    except Exception as exc:  # noqa: BLE001 - hook failures must fail open
        print(f"Glass Box event report skipped: {exc}", file=sys.stderr)
        return {"decision": "allow"}

    if phase == "post_tool":
        return {"decision": "allow"}

    run_id = str(posted.get("run_id") or invocation.get("run_id") or config.run_id or "")
    if not run_id:
        return {"decision": "allow"}
    try:
        control = request(
            "GET",
            _control_url(config.control_url_template, run_id, event),
            None,
            token=config.token,
            timeout_seconds=config.timeout_seconds,
        )
    except Exception as exc:  # noqa: BLE001 - hook failures must fail open
        print(f"Glass Box control check skipped: {exc}", file=sys.stderr)
        return {"decision": "allow"}

    action = str(control.get("action") or control.get("decision") or control.get("status") or "allow").lower()
    if action in {"deny", "braked", "brake", "abort", "aborted", "override", "wait"}:
        return {"decision": "deny", "reason": _deny_reason(control, action)}
    return {"decision": "allow"}


def _read_invocation() -> dict[str, Any]:
    raw = sys.stdin.read()
    if not raw.strip():
        raise ValueError("Vibe hook invocation was empty")
    decoded = json.loads(raw)
    if not isinstance(decoded, dict):
        raise ValueError("Vibe hook invocation must be a JSON object")
    return decoded


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Send Mistral Vibe hook events to Glass Box")
    parser.add_argument("phase", nargs="?", choices=("pre_tool", "post_tool", "before_tool", "after_tool"))
    args = parser.parse_args(argv)
    try:
        invocation = _read_invocation()
        phase = args.phase or str(invocation.get("hook_event_name") or "")
        response = handle_invocation(phase, invocation, AdapterConfig.from_env())
        print(json.dumps(response, separators=(",", ":")))
        return 0
    except Exception as exc:  # noqa: BLE001 - retain Vibe's normal fail-open hook path
        print(f"Glass Box hook error: {exc}", file=sys.stderr)
        print(json.dumps({"decision": "allow"}, separators=(",", ":")))
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
