# Kafka Topics & Streaming Architecture

## System Overview

CoSense Cloud uses a multi-layer streaming architecture combining **Confluent Kafka**, **QuixStreams** for Python-based stream processing, and **Confluent Cloud Flink** for SQL-based analytics and ML integration.

```
┌───────────────────────────────────────────────────────────────────────────────────┐
│                              DATA GENERATION LAYER                                 │
├───────────────────────────────────────────────────────────────────────────────────┤
│                                                                                    │
│   ┌─────────────┐                                                                  │
│   │  Simulator  │  Headless warehouse simulation engine                           │
│   │  (FastAPI)  │  • 200 robots, 100 humans                                       │
│   └──────┬──────┘  • 10Hz telemetry generation                                    │
│          │         • Physics-based movement & collision                            │
│          ▼                                                                         │
│   ┌──────────────────────────────────────────────────────────────────┐            │
│   │                    CONFLUENT KAFKA                                │            │
│   │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │            │
│   │  │ robot.telemetry │  │ human.telemetry │  │  zone.context   │  │            │
│   │  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘  │            │
│   └───────────┼────────────────────┼────────────────────┼───────────┘            │
│               │                    │                    │                         │
├───────────────┼────────────────────┼────────────────────┼─────────────────────────┤
│               ▼                    ▼                    ▼                         │
│           STREAM PROCESSING LAYER (QuixStreams + Python)                          │
├───────────────────────────────────────────────────────────────────────────────────┤
│                                                                                    │
│   ┌──────────────────────────────────────────────────────────────────┐            │
│   │                    STREAM PROCESSOR                               │            │
│   │                                                                   │            │
│   │  ┌─────────────────────────────────────────────────────────────┐ │            │
│   │  │ 1. WINDOWED JOIN (robot ↔ human ↔ zone)                     │ │            │
│   │  │    • 200ms tumbling windows                                  │ │            │
│   │  │    • QuixStreams StreamingDataFrame API                      │ │            │
│   │  └─────────────────────────────────────────────────────────────┘ │            │
│   │                              ▼                                   │            │
│   │  ┌─────────────────────────────────────────────────────────────┐ │            │
│   │  │ 2. RISK SCORING ENGINE                                      │ │            │
│   │  │    • Weighted multi-factor model                            │ │            │
│   │  │    • Real-time distance calculations                        │ │            │
│   │  │    • Sensor fusion (ultrasonic + BLE)                       │ │            │
│   │  └─────────────────────────────────────────────────────────────┘ │            │
│   │                              ▼                                   │            │
│   │  ┌─────────────────────────────────────────────────────────────┐ │            │
│   │  │ 3. DECISION ENGINE                                          │ │            │
│   │  │    • Threshold-based actions: STOP, SLOW, REROUTE, CONTINUE │ │            │
│   │  │    • Reason codes: CLOSE_PROXIMITY, HIGH_RELATIVE_SPEED,    │ │            │
│   │  │      BLE_PROXIMITY_DETECTED, SENSOR_DISAGREEMENT            │ │            │
│   │  └─────────────────────────────────────────────────────────────┘ │            │
│   │                              ▼                                   │            │
│   │  ┌─────────────────────────────────────────────────────────────┐ │            │
│   │  │ 4. ANOMALY DETECTION                                        │ │            │
│   │  │    • Pattern-based detection in Python                      │ │            │
│   │  │    • DECISION_RATE_SPIKE: >10 decisions in 30s window       │ │            │
│   │  │    • REPEATED_ROBOT_STOP: same robot stopped 3+ times/30s   │ │            │
│   │  │    • SENSOR_DISAGREEMENT_SPIKE: 3+ disagreements in 30s     │ │            │
│   │  └─────────────────────────────────────────────────────────────┘ │            │
│   └──────────────────────────────────────────────────────────────────┘            │
│               │                                                                    │
│               ▼                                                                    │
│   ┌──────────────────────────────────────────────────────────────────┐            │
│   │                    CONFLUENT KAFKA                                │            │
│   │  ┌──────────────────────┐  ┌───────────────────┐                 │            │
│   │  │ coordination.decisions│  │ coordination.state │                │            │
│   │  └──────────┬───────────┘  └─────────┬─────────┘                 │            │
│   │             │                        │                            │            │
│   │  ┌──────────┴────────────────────────┴───────────┐               │            │
│   │  │              anomaly.alerts                    │               │            │
│   │  └───────────────────┬───────────────────────────┘               │            │
│   └──────────────────────┼───────────────────────────────────────────┘            │
│                          │                                                         │
├──────────────────────────┼─────────────────────────────────────────────────────────┤
│                          ▼                                                         │
│              ANALYTICS LAYER (Confluent Cloud Flink)                               │
├───────────────────────────────────────────────────────────────────────────────────┤
│                                                                                    │
│   ┌──────────────────────────────────────────────────────────────────┐            │
│   │                    FLINK SQL PIPELINES                            │            │
│   │                                                                   │            │
│   │  ┌─────────────────────────────────────────────────────────────┐ │            │
│   │  │ SHIFT SUMMARY PIPELINE                                      │ │            │
│   │  │                                                              │ │            │
│   │  │  coordination.decisions                                     │ │            │
│   │  │         │                                                   │ │            │
│   │  │         ▼                                                   │ │            │
│   │  │  ┌─────────────────────────────────────────────────────┐   │ │            │
│   │  │  │ 5-MINUTE TUMBLE WINDOW AGGREGATION                  │   │ │            │
│   │  │  │ • COUNT(*) → decision_count                         │   │ │            │
│   │  │  │ • COUNT(STOP) → stop_count                          │   │ │            │
│   │  │  │ • COUNT(SLOW) → slow_count                          │   │ │            │
│   │  │  │ • COUNT(SENSOR_DISAGREEMENT) → sensor_disagreement  │   │ │            │
│   │  │  │ • AVG(risk_score), MAX(risk_score)                  │   │ │            │
│   │  │  │ • LISTAGG(events) → context_summary                 │   │ │            │
│   │  │  └─────────────────────────────────────────────────────┘   │ │            │
│   │  │         │                                                   │ │            │
│   │  │         ▼                                                   │ │            │
│   │  │  ┌─────────────────────────────────────────────────────┐   │ │            │
│   │  │  │ HEURISTIC CLASSIFICATION (AutoML-style)             │   │ │            │
│   │  │  │                                                      │   │ │            │
│   │  │  │ IF sensor_disagreement >= 3 → EQUIPMENT (85%)       │   │ │            │
│   │  │  │ IF stop_count >= 4 AND total >= 15 → HUMAN_FACTOR   │   │ │            │
│   │  │  │ IF slow_count >= 10 AND slow > stop*3 → ENVIRONMENTAL│   │ │            │
│   │  │  │ ELSE → NORMAL (90%)                                  │   │ │            │
│   │  │  └─────────────────────────────────────────────────────┘   │ │            │
│   │  │         │                                                   │ │            │
│   │  │         ▼                                                   │ │            │
│   │  │  ┌─────────────────────────────────────────────────────┐   │ │            │
│   │  │  │ GEMINI ML_PREDICT (via Flink AI connector)          │   │ │            │
│   │  │  │                                                      │   │ │            │
│   │  │  │ gemini-2.0-flash generates natural language summary │   │ │            │
│   │  │  │ "This shift saw high congestion in the east wing..." │   │ │            │
│   │  │  └─────────────────────────────────────────────────────┘   │ │            │
│   │  │         │                                                   │ │            │
│   │  │         ▼                                                   │ │            │
│   │  │  shift.summaries topic                                      │ │            │
│   │  └─────────────────────────────────────────────────────────────┘ │            │
│   └──────────────────────────────────────────────────────────────────┘            │
│                                                                                    │
├───────────────────────────────────────────────────────────────────────────────────┤
│                          APPLICATION LAYER                                         │
├───────────────────────────────────────────────────────────────────────────────────┤
│                                                                                    │
│   ┌─────────────┐     ┌──────────────────────────────────────────┐               │
│   │   Backend   │◄────│ Kafka Consumer (all decision/alert topics)│               │
│   │  (FastAPI)  │     └──────────────────────────────────────────┘               │
│   │             │                                                                  │
│   │  ┌─────────────────────────────────────────────────────────┐                 │
│   │  │ GEMINI OPERATOR COPILOT                                 │                 │
│   │  │ • 10 tools for querying state & controlling simulation  │                 │
│   │  │ • Automatic function calling                            │                 │
│   │  │ • On-demand summary generation (bypasses Flink)         │                 │
│   │  └─────────────────────────────────────────────────────────┘                 │
│   └──────┬──────┘                                                                 │
│          │                                                                         │
│          ▼                                                                         │
│   ┌─────────────┐                                                                 │
│   │ Control     │  React + TypeScript                                             │
│   │ Center UI   │  • Real-time warehouse map                                      │
│   │             │  • AI Alerts panel                                              │
│   │             │  • Performance Report (Gemini-generated)                        │
│   │             │  • Ask Gemini chat interface                                    │
│   └─────────────┘                                                                 │
│                                                                                    │
└───────────────────────────────────────────────────────────────────────────────────┘
```

## Kafka Topics

| Topic | Producer | Consumer | Format | Description |
|-------|----------|----------|--------|-------------|
| `robot.telemetry` | Simulator | Stream Processor | JSON | Robot position, velocity, heading, sensors @ 10Hz |
| `human.telemetry` | Simulator | Stream Processor | JSON | Human position, velocity @ 10Hz |
| `zone.context` | Simulator | Stream Processor | JSON | Visibility, connectivity, congestion levels |
| `coordination.decisions` | Stream Processor | Backend, Flink | JSON | STOP/SLOW/REROUTE decisions with reason codes |
| `coordination.state` | Stream Processor | Backend | JSON | Enriched robot state with risk scores |
| `anomaly.alerts` | Stream Processor | Backend | JSON | Pattern-detected anomalies |
| `shift.summaries` | Flink | Backend | Avro | 5-minute AI-generated performance summaries |

## Stream Processor (QuixStreams)

The stream processor is a Python service using **QuixStreams** for stateful stream processing on Kafka.

### Key Features

- **StreamingDataFrame API**: Pandas-like interface for stream transformations
- **Windowed Joins**: 200ms tumbling windows to join robot, human, and zone data
- **Stateful Processing**: Maintains robot state across messages
- **Pattern Detection**: Sliding window anomaly detection

### Risk Scoring Model

```python
risk_score = (
    proximity_risk * 0.35 +      # Distance to nearest human
    velocity_risk * 0.25 +        # Relative approach speed
    visibility_penalty * 0.15 +   # Degraded/poor visibility
    ble_risk * 0.10 +             # BLE proximity signal
    congestion_factor * 0.10 +    # Zone congestion level
    sensor_disagreement * 0.05    # Ultrasonic vs BLE mismatch
)
```

### Decision Thresholds

| Action | Condition |
|--------|-----------|
| `STOP` | `risk_score >= 0.8` OR `distance < 1.5m` |
| `SLOW` | `risk_score >= 0.5` OR `distance < 3.0m` |
| `REROUTE` | `risk_score >= 0.6` AND path blocked |
| `CONTINUE` | `risk_score < 0.5` |

### Reason Codes

| Code | Trigger |
|------|---------|
| `CLOSE_PROXIMITY` | Human within 3m |
| `HIGH_RELATIVE_SPEED` | Approach velocity > 2 m/s |
| `BLE_PROXIMITY_DETECTED` | BLE RSSI > -60 dBm |
| `SENSOR_DISAGREEMENT` | Ultrasonic and BLE readings conflict |
| `LOW_VISIBILITY` | Zone visibility degraded/poor |
| `HIGH_CONGESTION` | Zone congestion > 0.7 |

## Anomaly Detection

The stream processor implements pattern-based anomaly detection:

### DECISION_RATE_SPIKE
- **Window**: 30 seconds sliding
- **Threshold**: >10 non-CONTINUE decisions
- **Severity**: HIGH
- **Indicates**: Sudden congestion or environmental change

### REPEATED_ROBOT_STOP
- **Window**: 30 seconds per robot
- **Threshold**: Same robot stopped 3+ times
- **Severity**: HIGH
- **Indicates**: Persistent obstruction or sensor issue

### SENSOR_DISAGREEMENT_SPIKE
- **Window**: 30 seconds
- **Threshold**: 3+ disagreement events
- **Severity**: MEDIUM
- **Indicates**: Environmental interference or sensor degradation

## Flink SQL Analytics

Confluent Cloud Flink provides SQL-based stream analytics with AI integration.

### Shift Summary Pipeline

```sql
-- 5-minute tumbling window aggregation
CREATE VIEW shift_window_classified AS
SELECT
    window_start,
    window_end,
    COUNT(*) AS decision_count,
    COUNT(CASE WHEN action = 'STOP' THEN 1 END) AS stop_count,
    COUNT(CASE WHEN action = 'SLOW' THEN 1 END) AS slow_count,
    COUNT(CASE WHEN primary_reason = 'SENSOR_DISAGREEMENT' THEN 1 END) AS sensor_disagreement_count,
    AVG(risk_score) AS avg_risk_score,
    LISTAGG(CONCAT(robot_id, ': ', action), ' | ') AS context_summary,
    -- Heuristic classification
    CASE
        WHEN sensor_disagreement_count >= 3 THEN 'EQUIPMENT'
        WHEN stop_count >= 4 AND decision_count >= 15 THEN 'HUMAN_FACTOR'
        WHEN slow_count >= 10 AND slow_count > stop_count * 3 THEN 'ENVIRONMENTAL'
        ELSE 'NORMAL'
    END AS category
FROM TABLE(TUMBLE(TABLE decisions, DESCRIPTOR($rowtime), INTERVAL '5' MINUTE))
GROUP BY window_start, window_end;

-- Gemini AI summarization via ML_PREDICT
INSERT INTO shift.summaries
SELECT
    summary_id,
    window_start,
    window_end,
    decision_count,
    category,
    category_confidence,
    context_summary,
    ML_PREDICT('gemini_summarizer', prompt) AS ai_summary
FROM shift_window_classified;
```

### AutoML Classification Categories

| Category | Trigger | Confidence | Recommended Action |
|----------|---------|------------|-------------------|
| `NORMAL` | Low decision rate, few stops | 90% | Continue monitoring |
| `ENVIRONMENTAL` | High slow rate, proximity issues | 75% | Check visibility, obstacles |
| `HUMAN_FACTOR` | High stop rate, repeated interventions | 80% | Review traffic patterns |
| `EQUIPMENT` | Sensor disagreements | 85% | Sensor diagnostics needed |

## Gemini Integration

### Flink ML_PREDICT

```sql
CREATE MODEL gemini_summarizer
INPUT (prompt STRING)
OUTPUT (response STRING)
WITH (
    'provider' = 'googleai',
    'googleai.connection' = 'gemini-connection',
    'googleai.model' = 'gemini-2.0-flash',
    'googleai.system_instruction' = 'You are a warehouse safety analyst...'
);
```

### Backend Operator Copilot

The backend provides a Gemini-powered copilot with automatic function calling:

**Query Tools:**
- `get_robot_state(robot_id)` - Position, velocity, sensors
- `get_nearby_entities(robot_id)` - Humans/robots within range
- `get_decisions(filters)` - Recent coordination decisions
- `get_anomalies(filters)` - Active alerts
- `analyze_patterns()` - Decision distribution stats

**Control Tools:**
- `start_simulation()` / `stop_simulation()` / `reset_simulation()`
- `stop_robot(robot_id)` / `start_robot(robot_id)`

### On-Demand Summary Generation

When Flink summaries aren't available, the backend can generate summaries directly:

```python
POST /summary/generate

# Uses buffered decisions to:
# 1. Aggregate counts (decisions, stops, slows)
# 2. Apply heuristic classification
# 3. Call Gemini for natural language summary
```

## Message Schemas

### robot.telemetry
```json
{
  "robot_id": "robot-1",
  "timestamp": 1703145600000,
  "zone_id": "zone-c",
  "x": 25.5, "y": 12.3,
  "velocity": 1.5,
  "heading": 90.0,
  "motion_state": "moving",
  "ultrasonic_distance": 3.2,
  "ble_rssi": -55,
  "destination": "pack-1"
}
```

### coordination.decisions
```json
{
  "decision_id": "dec-1703145600000-robot-1",
  "robot_id": "robot-1",
  "timestamp": 1703145600000,
  "action": "SLOW",
  "reason_codes": ["CLOSE_PROXIMITY", "LOW_VISIBILITY"],
  "primary_reason": "CLOSE_PROXIMITY",
  "risk_score": 0.65,
  "nearest_human_distance": 2.1,
  "summary": "robot-1 slowing: human within 2.1m"
}
```

### anomaly.alerts
```json
{
  "alert_id": "dec-1703145600000",
  "alert_type": "DECISION_RATE_SPIKE",
  "severity": "HIGH",
  "robot_id": null,
  "detected_at": 1703145600000,
  "context": "15 decisions in last 30s vs expected 5"
}
```

### shift.summaries
```json
{
  "summary_id": "ss-1703145600",
  "window_start": "2024-12-21T10:00:00Z",
  "window_end": "2024-12-21T10:05:00Z",
  "decision_count": 47,
  "stop_count": 3,
  "slow_count": 38,
  "sensor_disagreement_count": 0,
  "category": "ENVIRONMENTAL",
  "category_confidence": 0.75,
  "context_summary": "robot-15: SLOW (CLOSE_PROXIMITY) | ...",
  "ai_summary": "This shift experienced high congestion with 38 slowdowns primarily due to close proximity events. Consider reviewing traffic patterns in the affected areas."
}
```

## Deployment Modes

| Mode | Kafka | Flink | Use Case |
|------|-------|-------|----------|
| **Local Docker** | `broker:29092` | N/A | Development |
| **Confluent Cloud** | `<cluster>.confluent.cloud:9092` | Confluent Cloud Flink | Production/Demo |

### Confluent Cloud Configuration

```bash
# .env
KAFKA_BROKERS=pkc-xxxxx.us-east1.gcp.confluent.cloud:9092
KAFKA_API_KEY=<key>
KAFKA_API_SECRET=<secret>
KAFKA_SECURITY_PROTOCOL=SASL_SSL
KAFKA_SASL_MECHANISM=PLAIN
```

## Data Flow Summary

1. **Simulator** generates 10Hz telemetry for 200 robots + 100 humans
2. **Stream Processor** (QuixStreams) joins streams, computes risk, emits decisions
3. **Stream Processor** detects anomalies using sliding window patterns
4. **Flink** (Confluent Cloud) aggregates 5-minute windows, classifies, calls Gemini
5. **Backend** consumes all topics, buffers for UI and Gemini copilot tools
6. **UI** displays real-time map, alerts, and AI-generated performance reports
