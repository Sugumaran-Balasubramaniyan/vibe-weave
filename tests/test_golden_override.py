"""Golden demo runs must not claim to resume without a worker."""

from fastapi.testclient import TestClient

from app.main import app


def test_golden_braked_run_rejects_authorization_without_active_worker():
    with TestClient(app) as client:
        run_id = client.post("/api/demo/load-golden").json()["run_id"]
        response = client.post(f"/api/runs/{run_id}/override/authorize")
    assert response.status_code == 409
    assert response.json()["detail"] == "No active worker for this run"
