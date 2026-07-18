"""Guarded fixture recovery must require evidence-backed authorization."""

import time

from fastapi.testclient import TestClient

from app.main import app, settings


def _wait_for_status(client: TestClient, run_id: str, status: str) -> dict:
    for _ in range(300):
        run = client.get(f"/api/runs/{run_id}").json()
        if run["status"] == status:
            return run
        time.sleep(0.01)
    raise AssertionError(f"Run {run_id} did not reach {status}")


def _braked_fixture_run(client: TestClient) -> str:
    run_id = client.post("/api/runs", json={"scenario_id": "db_migration_loop"}).json()["run_id"]
    assert client.post(f"/api/runs/{run_id}/start").status_code == 200
    _wait_for_status(client, run_id, "braked")
    return run_id


def test_fixture_question_or_missing_choice_cannot_resume(monkeypatch):
    monkeypatch.setattr(settings, "step_delay_ms_min", 1)
    monkeypatch.setattr(settings, "step_delay_ms_max", 1)
    with TestClient(app) as client:
        run_id = _braked_fixture_run(client)
        before = client.get(f"/api/runs/{run_id}").json()
        rejected = client.post(f"/api/runs/{run_id}/override", json={"rationale": "What happened?"})
        after = client.get(f"/api/runs/{run_id}").json()

    assert rejected.status_code == 422
    assert after["status"] == "braked"
    assert len(after["steps"]) == len(before["steps"])
    assert after["meta"].get("recovery_selection") is None


def test_fixture_rejects_unsafe_choice_without_changing_brake(monkeypatch):
    monkeypatch.setattr(settings, "step_delay_ms_min", 1)
    monkeypatch.setattr(settings, "step_delay_ms_max", 1)
    with TestClient(app) as client:
        run_id = _braked_fixture_run(client)
        rejected = client.post(
            f"/api/runs/{run_id}/override",
            json={"choice_id": "drop_and_recreate_users", "rationale": "Start clean"},
        )
        run = client.get(f"/api/runs/{run_id}").json()

    assert rejected.status_code == 422
    assert run["status"] == "braked"
    assert len(run["steps"]) == 6
    assert run["meta"].get("recovery_selection") is None


def test_fixture_selection_stays_braked_until_explicit_authorization(monkeypatch):
    monkeypatch.setattr(settings, "step_delay_ms_min", 1)
    monkeypatch.setattr(settings, "step_delay_ms_max", 1)
    with TestClient(app) as client:
        run_id = _braked_fixture_run(client)
        selected = client.post(
            f"/api/runs/{run_id}/override",
            json={"choice_id": "additive_email_migration", "rationale": "Preserve existing data."},
        )
        selected_run = client.get(f"/api/runs/{run_id}").json()

    assert selected.status_code == 200
    assert selected_run["status"] == "braked"
    assert len(selected_run["steps"]) == 6
    assert selected_run["meta"]["recovery_selection"] == {
        "choice_id": "additive_email_migration",
        "rationale": "Preserve existing data.",
        "authorizing": True,
        "evidence": [
            "db.migration.relation_exists repeated three times",
            "Existing users table must be preserved",
        ],
    }
    assert selected_run["events"][-1]["type"] == "recovery_selected"


def test_fixture_authorization_runs_only_selected_recovery(monkeypatch):
    monkeypatch.setattr(settings, "step_delay_ms_min", 1)
    monkeypatch.setattr(settings, "step_delay_ms_max", 1)
    with TestClient(app) as client:
        run_id = _braked_fixture_run(client)
        assert client.post(
            f"/api/runs/{run_id}/override",
            json={"choice_id": "additive_email_migration", "rationale": "Keep the table."},
        ).status_code == 200
        authorized = client.post(f"/api/runs/{run_id}/override/authorize")
        completed = _wait_for_status(client, run_id, "completed")
        duplicate = client.post(f"/api/runs/{run_id}/override/authorize")

    assert authorized.status_code == 200
    assert duplicate.status_code == 409
    assert completed["meta"]["recovery_authorized_choice_id"] == "additive_email_migration"
    assert [step["title"] for step in completed["steps"][-3:]] == [
        "Apply approved additive migration",
        "Alter users table (add email)",
        "Add GET /users route",
    ]
    assert "Keep the table." in completed["steps"][-3]["input_summary"]
    assert completed["events"][-1]["type"] == "recovery_authorized"


def test_fixture_cannot_authorize_without_a_selected_choice(monkeypatch):
    monkeypatch.setattr(settings, "step_delay_ms_min", 1)
    monkeypatch.setattr(settings, "step_delay_ms_max", 1)
    with TestClient(app) as client:
        run_id = _braked_fixture_run(client)
        response = client.post(f"/api/runs/{run_id}/override/authorize")
        run = client.get(f"/api/runs/{run_id}").json()

    assert response.status_code == 422
    assert run["status"] == "braked"
    assert len(run["steps"]) == 6
