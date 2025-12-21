# Kafka Topics & Data Flow

## Architecture Overview

```
┌───────────┐     ┌─────────┐     ┌──────────────────┐     ┌─────────┐
│ Simulator │ ──► │  KAFKA  │ ──► │ Stream Processor │ ──► │  KAFKA  │
└───────────┘     └─────────┘     └──────────────────┘     └────┬────┘
                                                                │
                       ┌────────────────────────────────────────┘
                       ▼
                  ┌─────────┐     ┌────┐
                  │ Backend │ ──► │ UI │
                  └─────────┘     └────┘
```

## Topics

| Topic | Producer | Consumer | Description |
|-------|----------|----------|-------------|
| `robot.telemetry` | Simulator | Stream Processor | Robot position, velocity, heading, sensors |
| `human.telemetry` | Simulator | Stream Processor | Human position, velocity |
| `zone.context` | Simulator | Stream Processor | Visibility, connectivity, congestion |
| `coordination.decisions` | Stream Processor | Backend | STOP/SLOW/REROUTE decisions with reason codes |
| `coordination.state` | Stream Processor | Backend | Enriched robot state with risk scores |

## Message Schemas

### robot.telemetry
```json
{
  "robot_id": "robot-1",
  "timestamp": 1703145600000,
  "zone_id": "zone-c",
  "x": 25.5,
  "y": 12.3,
  "velocity": 1.5,
  "heading": 90.0,
  "motion_state": "moving",
  "ultrasonic_distance": 3.2,
  "ble_rssi": -55,
  "destination": "pack-1"
}
```

### human.telemetry
```json
{
  "human_id": "human-1",
  "timestamp": 1703145600000,
  "zone_id": "zone-c",
  "x": 28.1,
  "y": 14.2,
  "velocity": 0.8,
  "heading": 180.0,
  "position_confidence": 0.95
}
```

### zone.context
```json
{
  "zone_id": "zone-c",
  "timestamp": 1703145600000,
  "visibility": "normal",
  "congestion_level": 0.45,
  "robot_count": 20,
  "human_count": 10,
  "connectivity": "normal"
}
```

### coordination.decisions
```json
{
  "decision_id": "dec-1703145600000-robot-1",
  "robot_id": "robot-1",
  "timestamp": 1703145600000,
  "zone_id": "zone-c",
  "action": "SLOW",
  "reason_codes": ["CLOSE_PROXIMITY", "LOW_VISIBILITY"],
  "primary_reason": "CLOSE_PROXIMITY",
  "risk_score": 0.65,
  "nearest_human_distance": 2.1,
  "summary": "robot-1 slowing: human within 2.1m"
}
```

## Data Flow

1. **Simulator** generates telemetry at 10Hz for all robots/humans
2. **Stream Processor** consumes telemetry, joins robot+human+zone data
3. **Stream Processor** computes risk scores using weighted factors:
   - Proximity (0.35)
   - Relative velocity (0.25)
   - Visibility (0.15)
   - BLE signal (0.10)
   - Congestion (0.10)
   - Sensor disagreement (0.05)
4. **Stream Processor** emits decisions when action changes (not CONTINUE)
5. **Stream Processor** POSTs decisions to Simulator to apply them
6. **Backend** consumes decisions, buffers for UI and Gemini tools

## Deployment Modes

| Mode | KAFKA_BROKERS | Auth |
|------|---------------|------|
| Local Docker | `broker:29092` | None |
| Confluent Cloud | `<cluster>.confluent.cloud:9092` | SASL_SSL |

For Confluent Cloud, set:
```bash
KAFKA_API_KEY=<key>
KAFKA_API_SECRET=<secret>
KAFKA_SECURITY_PROTOCOL=SASL_SSL
KAFKA_SASL_MECHANISM=PLAIN
```
