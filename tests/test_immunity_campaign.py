"""Contract coverage for the bounded prompt-injection immunity campaign."""

import time
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


def wait_for_completion(client: TestClient, run_id: str) -> dict:
    for _ in range(300):
        run = client.get(f"/api/runs/{run_id}").json()
        if run["status"] == "completed":
            return run
        assert run["status"] != "failed", run
        time.sleep(0.01)
    raise AssertionError("campaign did not complete")


def test_immunity_campaign_uses_existing_run_lifecycle_and_real_artifacts():
    with TestClient(app) as client:
        created = client.post("/api/runs", json={"scenario_id": "immunity_compiler_campaign"})
        assert created.status_code == 200
        run_id = created.json()["run_id"]
        assert client.post(f"/api/runs/{run_id}/start").status_code == 200
        run = wait_for_completion(client, run_id)

    meta = run["meta"]
    assert meta["campaign"] == {
        "id": "immunity_compiler_campaign",
        "fixture_id": "readme_prompt_injection",
        "status": "verified",
        "repair_attempts": 1,
        "max_repair_attempts": 1,
    }
    assert meta["attack_path"]["classification"] == "prompt_injection"
    assert meta["minimal_reproducer"]["filename"] == "README.md"
    assert meta["verified_policy_repair"]["verification"]["passed"] is True
    assert meta["verified_policy_repair"]["worktree_is_git"] is True
    assert (Path(meta["verified_policy_repair"]["worktree_path"]) / ".git").exists()
    for artifact in meta["campaign_artifacts"]:
        assert Path(artifact["path"]).is_file()


def test_campaign_events_are_persisted_for_sse_replay():
    with TestClient(app) as client:
        run_id = client.post("/api/runs", json={"scenario_id": "immunity_compiler_campaign"}).json()["run_id"]
        client.post(f"/api/runs/{run_id}/start")
        run = wait_for_completion(client, run_id)

    assert [event["type"] for event in run["events"]] == [
        "campaign_preparing",
        "campaign_detected",
        "campaign_repaired",
        "campaign_verified",
    ]
