"""API-level coverage of guarded fixture recovery."""

import time

from fastapi.testclient import TestClient

from app.main import app, settings


def wait_for_status(client: TestClient, run_id: str, expected_status: str) -> dict:
    for _ in range(300):
        run = client.get(f"/api/runs/{run_id}").json()
        if run["status"] == expected_status:
            return run
        time.sleep(0.01)
    raise AssertionError(f"Run {run_id} did not reach {expected_status}")


def test_authorized_choice_resumes_a_braked_fixture_run(monkeypatch):
    monkeypatch.setattr(settings, "step_delay_ms_min", 1)
    monkeypatch.setattr(settings, "step_delay_ms_max", 1)
    with TestClient(app) as client:
        run_id = client.post("/api/runs", json={"scenario_id": "db_migration_loop"}).json()["run_id"]
        assert client.post(f"/api/runs/{run_id}/start").status_code == 200
        wait_for_status(client, run_id, "braked")
        assert client.post(
            f"/api/runs/{run_id}/override",
            json={"choice_id": "additive_email_migration", "rationale": "Preserve the existing users table."},
        ).status_code == 200
        assert client.get(f"/api/runs/{run_id}").json()["status"] == "braked"
        assert client.post(f"/api/runs/{run_id}/override/authorize").status_code == 200
        completed_run = wait_for_status(client, run_id, "completed")

    assert completed_run["steps"][-3]["input_summary"] == (
        "Approved recovery: Use an additive email migration. "
        "Operator rationale: Preserve the existing users table."
    )
