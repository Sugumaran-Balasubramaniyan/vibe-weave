"""Contract tests for the project-local Mistral Vibe hook adapter."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


ADAPTER_PATH = Path(__file__).parents[1] / "scripts" / "glassbox_vibe_hook.py"
SPEC = importlib.util.spec_from_file_location("glassbox_vibe_hook", ADAPTER_PATH)
assert SPEC and SPEC.loader
hook = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = hook
SPEC.loader.exec_module(hook)


def config() -> hook.AdapterConfig:
    return hook.AdapterConfig(
        events_url="http://glassbox.test/api/v1/vibe/events",
        control_url_template="http://glassbox.test/api/v1/runs/{run_id}/control",
        token="test-token",
        run_id=None,
        timeout_seconds=0.1,
    )


def pre_invocation(**extra: object) -> dict[str, object]:
    invocation: dict[str, object] = {
        "hook_event_name": "pre_tool",
        "session_id": "vibe-session-7",
        "parent_session_id": "parent-session-1",
        "cwd": "/repo",
        "tool_name": "bash",
        "tool_call_id": "call-42",
        "tool_input": {"command": "pytest -q", "api_key": "secret-value"},
    }
    invocation.update(extra)
    return invocation


def test_normalizes_pre_tool_without_raw_arguments_or_secrets() -> None:
    event = hook.normalize_event("pre_tool", pre_invocation())

    assert event["event_id"] == "vibe-session-7:call-42:pre_tool"
    assert event["correlation_id"] == "vibe-session-7:call-42"
    assert event["session_id"] == "vibe-session-7"
    assert event["tool_name"] == "bash"
    assert event["phase"] == "pre_tool"
    assert event["status"] == "pending"
    assert "secret-value" not in str(event)
    assert "tool_input" not in event
    assert "raw" not in event


def test_normalization_drops_cwd_and_parent_session_and_bounds_identifiers() -> None:
    event = hook.normalize_event(
        "pre_tool",
        pre_invocation(
            session_id="Bearer session-secret-" + "x" * 200,
            parent_session_id="Bearer parent-session-secret",
            cwd="/repo/private-token-value",
            tool_call_id="token=call-secret-" + "y" * 200,
        ),
    )

    serialized = str(event)
    assert "parent-session-secret" not in serialized
    assert "/repo/private-token-value" not in serialized
    assert "session-secret" not in serialized
    assert "call-secret" not in serialized
    assert "parent_session_id" not in event
    assert "cwd" not in event
    assert len(event["session_id"]) <= hook.MAX_IDENTIFIER_CHARS
    assert len(event["tool_call_id"]) <= hook.MAX_IDENTIFIER_CHARS
    assert len(event["event_id"]) <= 200


def test_normalization_redacts_bearer_and_raw_token_values() -> None:
    event = hook.normalize_event(
        "post_tool",
        pre_invocation(
            hook_event_name="post_tool",
            tool_input={"command": "curl -H Authorization: Bearer actual-bearer-secret --token raw-cli-token"},
            tool_status="failure",
            tool_error="request failed with Bearer raw-error-token",
            tool_output_text="provider returned token=raw-output-token",
        ),
    )

    serialized = str(event)
    for secret in ("actual-bearer-secret", "raw-cli-token", "raw-error-token", "raw-output-token"):
        assert secret not in serialized
    assert "[REDACTED]" in serialized


def test_pre_and_post_events_have_distinct_ids_and_shared_correlation() -> None:
    pre = hook.normalize_event("pre_tool", pre_invocation())
    post = hook.normalize_event(
        "post_tool",
        pre_invocation(
            hook_event_name="post_tool",
            tool_status="failure",
            tool_error="database password=not-for-storage failed",
            tool_output_text="a long output transcript that must be summarized",
        ),
    )

    assert pre["event_id"] != post["event_id"]
    assert pre["correlation_id"] == post["correlation_id"]
    assert post["status"] == "error"
    assert "not-for-storage" not in str(post)
    assert post["error_signature"]


def test_pre_tool_posts_event_then_allows_when_backend_is_running() -> None:
    calls: list[tuple[str, str, object]] = []

    def request(method: str, url: str, payload: object, **_: object) -> dict[str, object]:
        calls.append((method, url, payload))
        if method == "POST":
            return {"run_id": "glass-run-1"}
        return {"action": "allow"}

    response = hook.handle_invocation("pre_tool", pre_invocation(), config(), request=request)

    assert response == {"decision": "allow"}
    assert calls[0][0] == "POST"
    assert calls[0][1].endswith("/api/v1/vibe/events")
    assert calls[1][0] == "GET"
    assert "/api/v1/runs/glass-run-1/control" in calls[1][1]


def test_pre_tool_denies_when_backend_reports_braked_override() -> None:
    def request(method: str, _url: str, _payload: object, **_: object) -> dict[str, object]:
        if method == "POST":
            return {"run_id": "glass-run-1"}
        return {
            "action": "override",
            "instruction": "Inspect the failing assertion before attempting another migration.",
        }

    response = hook.handle_invocation("pre_tool", pre_invocation(), config(), request=request)

    assert response["decision"] == "deny"
    assert "Inspect the failing assertion" in response["reason"]


def test_pre_tool_denies_when_backend_reports_abort() -> None:
    def request(method: str, _url: str, _payload: object, **_: object) -> dict[str, object]:
        if method == "POST":
            return {"run_id": "glass-run-1"}
        return {"status": "aborted", "reason": "Operator stopped this run."}

    response = hook.handle_invocation("pre_tool", pre_invocation(), config(), request=request)

    assert response == {"decision": "deny", "reason": "Operator stopped this run."}


def test_network_errors_fail_open() -> None:
    def request(*_args: object, **_kwargs: object) -> dict[str, object]:
        raise OSError("connection refused")

    response = hook.handle_invocation("pre_tool", pre_invocation(), config(), request=request)

    assert response == {"decision": "allow"}


def test_post_tool_only_reports_and_never_changes_tool_output() -> None:
    seen: list[dict[str, object]] = []

    def request(method: str, _url: str, payload: object, **_: object) -> dict[str, object]:
        assert method == "POST"
        assert isinstance(payload, dict)
        seen.append(payload)
        return {"run_id": "glass-run-1"}

    response = hook.handle_invocation(
        "post_tool",
        pre_invocation(hook_event_name="post_tool", tool_status="success", duration_ms=12.5),
        config(),
        request=request,
    )

    assert response == {"decision": "allow"}
    assert seen[0]["status"] == "ok"
    assert seen[0]["duration_ms"] == 12.5
