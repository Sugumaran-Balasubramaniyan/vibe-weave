"""Contract tests for authenticated Mistral Vibe hook ingestion."""

from fastapi.testclient import TestClient

from app.main import app, run_manager, settings


def _reset_vibe_state() -> None:
    run_manager.runs.clear()
    getattr(run_manager, "_vibe_sessions", {}).clear()
    getattr(run_manager, "_vibe_event_ids", set()).clear()


def test_post_tool_event_requires_token_and_creates_normalized_vibe_run(monkeypatch):
    monkeypatch.setattr(settings, "vibe_hook_token", "test-vibe-token", raising=False)
    _reset_vibe_state()
    payload = {
        "event_id": "evt-001",
        "session_id": "vibe-session-001",
        "event_type": "post_tool",
        "goal": "Fix the focused migration test",
        "tool_name": "bash",
        "input_summary": "pytest tests/test_migration.py -q",
        "output_summary": "1 failed: duplicate column email",
        "status": "error",
        "error_signature": "duplicate column email",
        "files_touched": [],
    }

    with TestClient(app) as client:
        denied = client.post("/api/v1/vibe/events", json=payload)
        accepted = client.post(
            "/api/v1/vibe/events",
            json=payload,
            headers={"X-GlassBox-Token": "test-vibe-token"},
        )

    assert denied.status_code == 401
    assert accepted.status_code == 200
    body = accepted.json()
    assert body["created"] is True
    run = body["run"]
    assert run["status"] == "running"
    assert run["meta"]["source"] == "vibe"
    assert run["meta"]["vibe_session_id"] == "vibe-session-001"
    assert run["steps"] == [{
        "id": run["steps"][0]["id"],
        "index": 0,
        "timestamp": run["steps"][0]["timestamp"],
        "type": "tool_call",
        "title": "Vibe tool: bash",
        "action": "bash",
        "input_summary": "pytest tests/test_migration.py -q",
        "output_summary": "1 failed: duplicate column email",
        "status": "error",
        "error_signature": "duplicate column email",
        "files_touched": [],
        "raw": None,
    }]
    assert run["entropy"]["braking"] is False


def test_vibe_loop_brakes_then_returns_one_override_instruction(monkeypatch):
    monkeypatch.setattr(settings, "vibe_hook_token", "test-vibe-token", raising=False)
    _reset_vibe_state()
    headers = {"X-GlassBox-Token": "test-vibe-token"}

    with TestClient(app) as client:
        for number in range(3):
            response = client.post(
                "/api/v1/vibe/events",
                headers=headers,
                json={
                    "event_id": f"evt-loop-{number}",
                    "session_id": "vibe-loop-session",
                    "event_type": "post_tool",
                    "goal": "Repair the migration",
                    "tool_name": "bash",
                    "input_summary": "pytest tests/test_migration.py -q",
                    "output_summary": "duplicate column email",
                    "status": "error",
                    "error_signature": "duplicate column email",
                    "files_touched": [],
                },
            )

        assert response.status_code == 200
        run = response.json()["run"]
        assert run["status"] == "braked"
        assert response.json()["braked"] is True
        assert client.get(
            "/api/v1/vibe/control",
            params={"session_id": "vibe-loop-session"},
            headers=headers,
        ).json()["action"] == "wait"

        override = client.post(
            f"/api/runs/{run["run_id"]}/override",
            json={"text": "Inspect the existing migration before editing it."},
        )
        control = client.get(
            "/api/v1/vibe/control",
            params={"session_id": "vibe-loop-session"},
            headers=headers,
        )
        follow_up_control = client.get(
            "/api/v1/vibe/control",
            params={"session_id": "vibe-loop-session"},
            headers=headers,
        )

    assert override.status_code == 200
    assert control.json() == {
        "action": "override_instruction",
        "run_id": run["run_id"],
        "instruction": "Inspect the existing migration before editing it.",
    }
    assert follow_up_control.json()["action"] == "allow"


def test_compressor_loads_the_checked_in_prompt_file():
    from app.compressor import Compressor

    assert "Be faithful to the steps" in Compressor(settings).system_prompt


def test_replayed_vibe_event_is_idempotent(monkeypatch):
    monkeypatch.setattr(settings, "vibe_hook_token", "test-vibe-token", raising=False)
    _reset_vibe_state()
    payload = {
        "event_id": "evt-replayed",
        "session_id": "vibe-replayed-session",
        "event_type": "post_tool",
        "tool_name": "read",
        "input_summary": "README.md",
        "output_summary": "read",
        "status": "ok",
    }
    with TestClient(app) as client:
        first = client.post("/api/v1/vibe/events", json=payload, headers={"X-GlassBox-Token": "test-vibe-token"})
        replay = client.post("/api/v1/vibe/events", json=payload, headers={"X-GlassBox-Token": "test-vibe-token"})

    assert first.status_code == replay.status_code == 200
    assert replay.json()["deduplicated"] is True
    assert len(replay.json()["run"]["steps"]) == 1


def test_run_scoped_vibe_control_endpoint_matches_hook_contract(monkeypatch):
    monkeypatch.setattr(settings, "vibe_hook_token", "test-vibe-token", raising=False)
    _reset_vibe_state()
    headers = {"X-GlassBox-Token": "test-vibe-token"}
    with TestClient(app) as client:
        event = client.post(
            "/api/v1/vibe/events",
            headers=headers,
            json={
                "event_id": "evt-control",
                "session_id": "vibe-control-session",
                "event_type": "post_tool",
                "tool_name": "read",
                "status": "ok",
            },
        )
        run_id = event.json()["run"]["run_id"]
        control = client.get(
            f"/api/v1/runs/{run_id}/control",
            params={"session_id": "vibe-control-session", "tool_call_id": "call-001"},
            headers=headers,
        )

    assert control.status_code == 200
    assert control.json() == {"action": "allow", "run_id": run_id}


def test_adapter_shaped_pre_tool_event_resolves_a_vibe_run(monkeypatch):
    monkeypatch.setattr(settings, "vibe_hook_token", "test-vibe-token", raising=False)
    _reset_vibe_state()
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/vibe/events",
            headers={"X-GlassBox-Token": "test-vibe-token"},
            json={
                "schema_version": 1,
                "source": "mistral-vibe",
                "event_id": "session-42:call-7:pre_tool",
                "correlation_id": "session-42:call-7",
                "phase": "pre_tool",
                "event_type": "tool.pre",
                "session_id": "session-42",
                "tool_name": "bash",
                "tool_call_id": "call-7",
                "input_summary": "pytest -q",
                "status": "pending",
            },
        )

    assert response.status_code == 200
    assert response.json()["run_id"] == response.json()["run"]["run_id"]
    assert response.json()["run"]["steps"] == []


def test_adapter_shaped_post_tool_event_is_scored(monkeypatch):
    monkeypatch.setattr(settings, "vibe_hook_token", "test-vibe-token", raising=False)
    _reset_vibe_state()
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/vibe/events",
            headers={"X-GlassBox-Token": "test-vibe-token"},
            json={
                "event_id": "session-99:call-2:post_tool",
                "phase": "post_tool",
                "event_type": "tool.post",
                "session_id": "session-99",
                "tool_name": "bash",
                "tool_call_id": "call-2",
                "input_summary": "pytest -q",
                "output_summary": "assertion failed",
                "status": "failure",
                "error_signature": "assertion failed",
            },
        )

    assert response.status_code == 200
    assert response.json()["run"]["steps"][0]["status"] == "error"
    assert response.json()["run"]["entropy"] is not None


def test_vibe_override_starts_a_new_entropy_window_for_successful_recovery(monkeypatch):
    monkeypatch.setattr(settings, "vibe_hook_token", "test-vibe-token", raising=False)
    _reset_vibe_state()
    headers = {"X-GlassBox-Token": "test-vibe-token"}
    session_id = "vibe-recovery-session"

    with TestClient(app) as client:
        for number in range(3):
            failed = client.post(
                "/api/v1/vibe/events",
                headers=headers,
                json={
                    "event_id": f"recovery-error-{number}",
                    "session_id": session_id,
                    "phase": "post_tool",
                    "event_type": "tool.post",
                    "tool_name": "bash",
                    "input_summary": "pytest tests/test_migration.py -q",
                    "output_summary": "duplicate column email",
                    "status": "failure",
                    "error_signature": "duplicate column email",
                },
            )
        run_id = failed.json()["run_id"]
        assert client.post(
            f"/api/runs/{run_id}/override",
            json={"text": "Inspect the existing migration before editing it."},
        ).status_code == 200
        assert client.get(
            f"/api/v1/runs/{run_id}/control",
            params={"session_id": session_id, "tool_call_id": "recovery-call"},
            headers=headers,
        ).json()["action"] == "override"
        recovered = client.post(
            "/api/v1/vibe/events",
            headers=headers,
            json={
                "event_id": "recovery-success",
                "session_id": session_id,
                "phase": "post_tool",
                "event_type": "tool.post",
                "tool_name": "edit",
                "input_summary": "apply an additive migration",
                "output_summary": "migration updated",
                "status": "success",
                "files_touched": ["migrations/001_add_email.sql"],
            },
        )

    assert recovered.status_code == 200
    assert recovered.json()["braked"] is False
    assert recovered.json()["run"]["status"] == "running"
