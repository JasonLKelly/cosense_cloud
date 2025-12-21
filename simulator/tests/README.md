# Simulator Tests

This directory contains tests for the CoSense Cloud simulator service.

## Test Structure

```
tests/
├── unit/                    # No external dependencies
│   ├── conftest.py          # Fixtures for unit tests
│   ├── test_entities.py     # Robot, Human, Zone tests
│   ├── test_world.py        # World engine tests
│   └── test_scenarios.py    # Demo scenario tests
│
├── integration/             # Requires setup (see below)
│   ├── conftest.py          # Fixtures for integration tests
│   └── test_api.py          # FastAPI endpoint tests
│
└── README.md                # This file
```

## Prerequisites

### For Unit Tests

Unit tests have **no external dependencies**. They test pure Python logic.

```bash
cd simulator
uv pip install -e ".[dev]"
# or: pip install -e ".[dev]"
```

### For Integration Tests

Integration tests require:
- Python packages installed (same as unit tests)
- **No Kafka required** - Kafka producer is mocked

```bash
cd simulator
uv pip install -e ".[dev]"
```

## Running Tests

### Run All Tests

```bash
cd simulator
pytest tests/ -v
```

### Run Only Unit Tests

```bash
pytest tests/unit/ -v
```

### Run Only Integration Tests

```bash
pytest tests/integration/ -v
```

### Run Specific Test File

```bash
pytest tests/unit/test_entities.py -v
```

### Run Specific Test Class

```bash
pytest tests/unit/test_entities.py::TestRobot -v
```

### Run Specific Test

```bash
pytest tests/unit/test_entities.py::TestRobot::test_robot_stop_command -v
```

## Test Categories

### Unit Tests (`tests/unit/`)

| File | Description |
|------|-------------|
| `test_entities.py` | Tests for Robot, Human, and Zone classes |
| `test_world.py` | Tests for World engine (tick, sensors, scaling) |
| `test_scenarios.py` | Demo scenarios showing key behaviors |

### Integration Tests (`tests/integration/`)

| File | Description |
|------|-------------|
| `test_api.py` | FastAPI endpoint tests (uses TestClient) |

## Key Scenarios Tested

1. **Robot STOP command**: Robot decelerates and stops when commanded
2. **Robot SLOW command**: Robot limits speed to 0.5 m/s
3. **Sensor detection**: Ultrasonic (10m) and BLE (15m) ranges
4. **Zone conditions**: Visibility and connectivity toggles
5. **Scaling**: Dynamic addition of robots and humans
6. **Multi-robot coordination**: Each robot responds independently

## Writing New Tests

### Unit Test Template

```python
# tests/unit/test_myfeature.py

import pytest
from entities import Robot, Human, Zone
from world import World

class TestMyFeature:
    """Tests for my feature."""

    def test_basic_behavior(self, world):
        """Test the basic behavior."""
        # Arrange
        robot = world.robots[0]

        # Act
        robot.do_something()

        # Assert
        assert robot.state == "expected"
```

### Integration Test Template

```python
# tests/integration/test_myendpoint.py

import pytest
from fastapi.testclient import TestClient

class TestMyEndpoint:
    """Tests for /my-endpoint"""

    def test_returns_200(self, client: TestClient):
        """Endpoint returns success."""
        response = client.get("/my-endpoint")
        assert response.status_code == 200
```

## Fixtures

### Unit Test Fixtures (conftest.py)

- `rng`: Deterministic random generator (seed=42)
- `zone`: Test zone (50x30m)
- `robot`: Test robot at zone center
- `human`: Test human at zone center
- `world`: Test world with 2 robots, 2 humans (no Kafka)
- `world_close_proximity`: World with robot and human 2m apart

### Integration Test Fixtures

- `client`: FastAPI TestClient with mock world injected
