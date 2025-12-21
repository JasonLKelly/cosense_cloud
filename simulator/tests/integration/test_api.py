"""
Integration tests for FastAPI endpoints.

PREREQUISITES:
  1. Install the simulator package:
     cd simulator
     uv pip install -e ".[dev]"

  2. Run tests:
     pytest tests/integration/test_api.py -v

WHAT THESE TESTS DO:
  - Test HTTP endpoints using FastAPI TestClient
  - Mock the World to avoid Kafka dependency
  - Verify request/response contracts

WHAT THESE TESTS DO NOT DO:
  - Connect to Kafka (mocked out)
  - Test actual message production
  - Test the simulation loop (see unit tests)
"""

import random

import pytest
from fastapi.testclient import TestClient

from src.entities import Robot, Human, Zone
from src.world import World
import src.main as main_module
from src.main import app


@pytest.fixture
def client():
    """
    Create test client with mock world (no Kafka).

    This fixture:
    - Starts the TestClient (which runs app lifespan)
    - Replaces the world with a controlled test world
    - Provides a TestClient for making requests
    - Cleans up after tests
    """
    with TestClient(app, raise_server_exceptions=False) as test_client:
        # Replace the world AFTER lifespan runs (lifespan creates default world)
        main_module.world = World(
            zone=Zone(zone_id="test-zone", width=50.0, height=30.0),
            robots=[
                Robot(robot_id="robot-1", zone_id="test-zone", x=10.0, y=10.0),
                Robot(robot_id="robot-2", zone_id="test-zone", x=40.0, y=20.0),
            ],
            humans=[
                Human(human_id="human-1", zone_id="test-zone", x=15.0, y=15.0),
            ],
            rng=random.Random(42),
            producer=None,  # No Kafka
        )
        yield test_client

    # Cleanup
    main_module.world = None
    main_module.simulation_task = None


class TestHealthEndpoint:
    """Tests for GET /health"""

    def test_health_returns_200(self, client: TestClient):
        """Health check returns success."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_response_structure(self, client: TestClient):
        """Health response has expected fields."""
        response = client.get("/health")
        data = response.json()

        assert data["status"] == "healthy"
        assert "running" in data
        assert data["running"] is False


class TestStateEndpoint:
    """Tests for GET /state"""

    def test_state_returns_200(self, client: TestClient):
        """State endpoint returns success."""
        response = client.get("/state")
        assert response.status_code == 200

    def test_state_response_structure(self, client: TestClient):
        """State response has all required fields."""
        response = client.get("/state")
        data = response.json()

        assert "sim_time" in data
        assert "running" in data
        assert "zone" in data
        assert "robots" in data
        assert "humans" in data

    def test_state_includes_all_robots(self, client: TestClient):
        """State includes all robots."""
        response = client.get("/state")
        data = response.json()

        assert len(data["robots"]) == 2
        robot_ids = [r["robot_id"] for r in data["robots"]]
        assert "robot-1" in robot_ids
        assert "robot-2" in robot_ids

    def test_state_robot_fields(self, client: TestClient):
        """Each robot has required fields."""
        response = client.get("/state")
        robot = response.json()["robots"][0]

        required = ["robot_id", "x", "y", "velocity", "heading", "motion_state", "commanded_action"]
        for field in required:
            assert field in robot, f"Missing field: {field}"


class TestScenarioStartStop:
    """
    Tests for scenario control endpoints.

    NOTE: We skip tests that actually start the simulation loop
    because the async task doesn't play well with TestClient.
    The start/stop logic is tested at the unit level instead.
    """

    @pytest.mark.skip(reason="Async simulation loop hangs with TestClient")
    def test_start_returns_started(self, client: TestClient):
        """POST /scenario/start returns started status."""
        response = client.post("/scenario/start")
        assert response.status_code == 200
        assert response.json()["status"] == "started"

        # Cleanup
        client.post("/scenario/stop")

    @pytest.mark.skip(reason="Async simulation loop hangs with TestClient")
    def test_start_when_running_returns_already_running(self, client: TestClient):
        """Starting when already running returns already_running."""
        client.post("/scenario/start")

        response = client.post("/scenario/start")
        assert response.json()["status"] == "already_running"

        client.post("/scenario/stop")

    @pytest.mark.skip(reason="Async simulation loop hangs with TestClient")
    def test_stop_returns_stopped(self, client: TestClient):
        """POST /scenario/stop returns stopped status."""
        client.post("/scenario/start")

        response = client.post("/scenario/stop")
        assert response.status_code == 200
        assert response.json()["status"] == "stopped"

    def test_reset_returns_reset(self, client: TestClient):
        """POST /scenario/reset returns reset status."""
        response = client.post("/scenario/reset")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "reset"
        assert "robot_count" in data
        assert "human_count" in data


class TestScenarioToggle:
    """Tests for POST /scenario/toggle"""

    def test_toggle_visibility(self, client: TestClient):
        """Toggle visibility to poor."""
        response = client.post("/scenario/toggle", json={"visibility": "poor"})
        assert response.status_code == 200
        assert response.json()["visibility"] == "poor"

    def test_toggle_connectivity(self, client: TestClient):
        """Toggle connectivity to degraded."""
        response = client.post("/scenario/toggle", json={"connectivity": "degraded"})
        assert response.status_code == 200
        assert response.json()["connectivity"] == "degraded"

    def test_toggle_both(self, client: TestClient):
        """Toggle both conditions."""
        response = client.post("/scenario/toggle", json={
            "visibility": "degraded",
            "connectivity": "offline"
        })
        assert response.status_code == 200

        data = response.json()
        assert data["visibility"] == "degraded"
        assert data["connectivity"] == "offline"

    def test_toggle_persists_in_state(self, client: TestClient):
        """Toggle changes appear in GET /state."""
        client.post("/scenario/toggle", json={"visibility": "poor"})

        response = client.get("/state")
        assert response.json()["zone"]["visibility"] == "poor"


class TestScenarioScale:
    """Tests for POST /scenario/scale"""

    def test_scale_add_robots(self, client: TestClient):
        """Add robots increases count."""
        response = client.post("/scenario/scale", json={"robots": 3})
        assert response.status_code == 200
        assert response.json()["robot_count"] == 5  # 2 + 3

    def test_scale_add_humans(self, client: TestClient):
        """Add humans increases count."""
        response = client.post("/scenario/scale", json={"humans": 4})
        assert response.status_code == 200
        assert response.json()["human_count"] == 5  # 1 + 4

    def test_scale_zero_is_noop(self, client: TestClient):
        """Scaling by zero does nothing."""
        response = client.post("/scenario/scale", json={"robots": 0})
        assert response.json()["robot_count"] == 2


class TestDecisionEndpoint:
    """Tests for POST /decision"""

    def test_apply_stop_decision(self, client: TestClient):
        """Apply STOP decision."""
        response = client.post("/decision", json={
            "robot_id": "robot-1",
            "action": "STOP"
        })
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "applied"
        assert data["robot_id"] == "robot-1"
        assert data["action"] == "STOP"

    def test_decision_reflects_in_state(self, client: TestClient):
        """Applied decision shows in state."""
        client.post("/decision", json={
            "robot_id": "robot-1",
            "action": "STOP"
        })

        response = client.get("/state")
        robot = next(r for r in response.json()["robots"] if r["robot_id"] == "robot-1")
        assert robot["commanded_action"] == "STOP"

    @pytest.mark.parametrize("action", ["CONTINUE", "SLOW", "STOP", "REROUTE"])
    def test_all_action_types(self, client: TestClient, action: str):
        """All action types can be applied."""
        response = client.post("/decision", json={
            "robot_id": "robot-1",
            "action": action
        })
        assert response.status_code == 200
        assert response.json()["action"] == action
