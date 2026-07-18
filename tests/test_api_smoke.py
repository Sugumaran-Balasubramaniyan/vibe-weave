"""Smoke tests for API endpoints."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestHealth:
    """Test health endpoint."""
    
    def test_health_endpoint(self, client):
        """Test /health returns ok."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestScenarios:
    """Test scenarios endpoint."""
    
    def test_list_scenarios(self, client):
        """Test listing available scenarios."""
        response = client.get("/api/scenarios")
        assert response.status_code == 200
        data = response.json()
        assert "scenarios" in data
        assert isinstance(data["scenarios"], list)
        # Should have at least db_migration_loop
        scenario_ids = [s["id"] for s in data["scenarios"]]
        assert "db_migration_loop" in scenario_ids


class TestRuns:
    """Test runs endpoints."""
    
    def test_create_run(self, client):
        """Test creating a new run."""
        response = client.post(
            "/api/runs",
            json={"scenario_id": "db_migration_loop"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "run_id" in data
        assert data["status"] == "idle"
        assert data["scenario_id"] == "db_migration_loop"
    
    def test_get_run(self, client):
        """Test getting a specific run."""
        # Create a run first
        create_response = client.post(
            "/api/runs",
            json={"scenario_id": "db_migration_loop"}
        )
        run_id = create_response.json()["run_id"]
        
        # Get the run
        response = client.get(f"/api/runs/{run_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["run_id"] == run_id
    
    def test_get_nonexistent_run(self, client):
        """Test getting a nonexistent run."""
        response = client.get("/api/runs/nonexistent")
        assert response.status_code == 404
    
    def test_start_run(self, client):
        """Test starting a run."""
        # Create a run
        create_response = client.post(
            "/api/runs",
            json={"scenario_id": "db_migration_loop"}
        )
        run_id = create_response.json()["run_id"]
        
        # Start the run
        response = client.post(f"/api/runs/{run_id}/start")
        assert response.status_code == 200
        assert response.json()["message"] == "Run started"
    
    def test_start_non_idle_run(self, client):
        """Test starting a non-idle run returns 409."""
        # Create and start a run
        create_response = client.post(
            "/api/runs",
            json={"scenario_id": "db_migration_loop"}
        )
        run_id = create_response.json()["run_id"]
        client.post(f"/api/runs/{run_id}/start")
        
        # Try to start again
        response = client.post(f"/api/runs/{run_id}/start")
        assert response.status_code == 409


class TestOverride:
    """Test override endpoint."""
    
    def test_override_not_braked(self, client):
        """Test override on non-braked run returns 409."""
        # Create a run
        create_response = client.post(
            "/api/runs",
            json={"scenario_id": "db_migration_loop"}
        )
        run_id = create_response.json()["run_id"]
        
        # Try to override without starting
        response = client.post(
            f"/api/runs/{run_id}/override",
            json={"text": "test override"}
        )
        assert response.status_code == 409
    
    def test_override_validation(self, client):
        """Test override validation - requires braked status."""
        # Create a run (don't start it)
        create_response = client.post(
            "/api/runs",
            json={"scenario_id": "db_migration_loop"}
        )
        run_id = create_response.json()["run_id"]
        
        # Try to override without starting - should fail (not idle -> braked transition)
        response = client.post(
            f"/api/runs/{run_id}/override",
            json={"text": "test override"}
        )
        assert response.status_code == 409


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
