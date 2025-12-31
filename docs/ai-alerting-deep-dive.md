# AI-Powered Alerting: A Deep Dive

This document provides a comprehensive technical overview of CoSense Cloud's AI alerting system, designed for hackathon judges evaluating our Confluent + Google Cloud integration.

## Executive Summary

CoSense Cloud implements **real-time AI alerting** that detects anomalies in streaming warehouse telemetry and enriches them with natural language explanations—all within the Confluent streaming platform. This represents true "AI on data in motion" where the entire pipeline from raw sensor data to actionable, AI-explained alerts happens in milliseconds.

**Key Technologies:**
- **Confluent Cloud Flink SQL** - Stream processing and anomaly detection
- **ML_DETECT_ANOMALIES** - Built-in ARIMA-based anomaly detection
- **ML_PREDICT with Vertex AI** - Real-time Gemini integration for explanations
- **Apache Kafka** - Event backbone connecting all components

---

## Architecture Overview

```
                         DATA FLOW: Telemetry → Decisions → Anomalies → Explanations
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    CONFLUENT CLOUD                                           │
│                                                                                              │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────────────────┐   │
│  │   robot.    │     │ coordination│     │  anomaly.   │     │  anomaly.alerts.        │   │
│  │  telemetry  │────▶│  .decisions │────▶│   alerts    │────▶│  enriched               │   │
│  └─────────────┘     └─────────────┘     └─────────────┘     └─────────────────────────┘   │
│        │                   │                   │                        │                   │
│        │                   │                   │                        │                   │
│        ▼                   ▼                   ▼                        ▼                   │
│  ┌───────────────────────────────────────────────────────────────────────────────────────┐ │
│  │                              FLINK SQL COMPUTE POOL                                    │ │
│  │                                                                                        │ │
│  │   ┌─────────────────┐    ┌─────────────────────┐    ┌─────────────────────────────┐  │ │
│  │   │  QuixStreams    │    │  10s TUMBLE Window  │    │  ML_PREDICT                 │  │ │
│  │   │  Python DSL     │    │  Aggregation        │    │  (Gemini via Vertex AI)     │  │ │
│  │   │                 │    │                     │    │                             │  │ │
│  │   │  • Risk calc    │    │  • decision_count   │    │  • Prompt construction      │  │ │
│  │   │  • STOP/SLOW    │    │  • stop_count       │    │  • Context injection        │  │ │
│  │   │  • Reason codes │    │  • sensor_errors    │    │  • Natural language output  │  │ │
│  │   └─────────────────┘    └─────────────────────┘    └─────────────────────────────┘  │ │
│  │                                    │                               │                   │ │
│  │                                    ▼                               │                   │ │
│  │                          ┌─────────────────────┐                   │                   │ │
│  │                          │ ML_DETECT_ANOMALIES │                   │                   │ │
│  │                          │                     │                   │                   │ │
│  │                          │  ARIMA-based        │                   │                   │ │
│  │                          │  • forecast_value   │───────────────────┘                   │ │
│  │                          │  • confidence bounds│                                       │ │
│  │                          │  • is_anomaly flag  │                                       │ │
│  │                          └─────────────────────┘                                       │ │
│  └───────────────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                              │
└──────────────────────────────────────────────────────────────────────────────────────────────┘
                                              │
                                              ▼
                                    ┌───────────────────┐
                                    │  Control Center   │
                                    │  React UI         │
                                    │                   │
                                    │  • Live alerts    │
                                    │  • AI explanation │
                                    │  • Dismiss/action │
                                    └───────────────────┘
```

---

## The Three-Stage Pipeline

### Stage 1: Real-Time Risk Assessment (QuixStreams)

The first stage processes raw telemetry into coordination decisions using a Python stream processor built on **QuixStreams** (Confluent's Python streaming library).

**Input Topics:**
- `robot.telemetry` - Position, velocity, heading, sensor readings
- `human.telemetry` - Worker positions and movement

**Processing Logic:**
```python
# Simplified risk calculation
risk_score = (
    proximity_risk * 0.45 +      # Distance to nearest human
    relative_speed_risk * 0.30 + # Closing velocity
    ble_proximity_risk * 0.15 +  # Bluetooth beacon detection
    sensor_disagreement * 0.10   # Camera vs ultrasonic mismatch
)

# Action determination
if risk_score >= 0.7:
    action = "STOP"      # Immediate halt
elif risk_score >= 0.4:
    action = "SLOW"      # Reduce speed
else:
    action = "CONTINUE"  # Proceed normally
```

**Output Topic:** `coordination.decisions`
```json
{
  "decision_id": "dec-1735625400-robot-42",
  "robot_id": "robot-42",
  "action": "STOP",
  "risk_score": 0.752,
  "reason_codes": ["CLOSE_PROXIMITY", "HIGH_RELATIVE_SPEED"],
  "primary_reason": "CLOSE_PROXIMITY",
  "summary": "robot-42 stopping due to human within 1.2m",
  "event_time": "2025-12-31T06:30:00Z"
}
```

---

### Stage 2: Anomaly Detection (Flink SQL + ML_DETECT_ANOMALIES)

The second stage uses **Confluent Flink SQL** to detect unusual patterns in the decision stream. This is where Confluent's built-in ML capabilities shine.

#### Windowed Aggregation

First, we aggregate decisions into 10-second tumbling windows:

```sql
CREATE VIEW decision_rate_windowed AS
SELECT
    window_start,
    window_end,
    window_time,
    COUNT(*) AS decision_count,
    COUNT(CASE WHEN action = 'STOP' THEN 1 END) AS stop_count,
    COUNT(CASE WHEN primary_reason = 'SENSOR_DISAGREEMENT' THEN 1 END) AS sensor_disagreement_count,
    AVG(risk_score) AS avg_risk_score
FROM TABLE(
    TUMBLE(TABLE coordination_decisions, DESCRIPTOR(event_time), INTERVAL '10' SECOND)
)
GROUP BY window_start, window_end, window_time;
```

#### ARIMA-Based Anomaly Detection

Then, we apply `ML_DETECT_ANOMALIES` to identify statistical outliers:

```sql
CREATE VIEW decision_rate_anomalies AS
SELECT
    window_time,
    decision_count,
    ML_DETECT_ANOMALIES(
        CAST(decision_count AS DOUBLE),
        window_time,
        JSON_OBJECT(
            'minTrainingSize' VALUE 6,         -- 1 minute of history
            'maxTrainingSize' VALUE 60,        -- 10 minutes max
            'confidencePercentage' VALUE 95.0, -- 95% confidence interval
            'enableStl' VALUE false            -- No seasonality
        )
    ) OVER (
        ORDER BY window_time
        RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS anomaly_result
FROM decision_rate_windowed;
```

**How ML_DETECT_ANOMALIES Works:**
1. Maintains a sliding window of historical values
2. Fits an ARIMA model to predict the next value
3. Calculates confidence bounds based on prediction error
4. Flags the current value as anomalous if outside bounds

#### Anomaly Types Detected

| Alert Type | Detection Logic | Business Meaning |
|------------|-----------------|------------------|
| `DECISION_RATE_SPIKE` | Decision count exceeds ARIMA upper bound | Sudden increase in safety interventions—possible incident |
| `REPEATED_ROBOT_STOP` | Same robot stops 2+ times in 30 seconds | Robot trapped or environmental hazard |
| `SENSOR_DISAGREEMENT_SPIKE` | 2+ sensor mismatches in 10 seconds | Potential sensor malfunction or tampering |

**Output Topic:** `anomaly.alerts`
```json
{
  "alert_id": "dra-1735625400",
  "alert_type": "DECISION_RATE_SPIKE",
  "detected_at": "2025-12-31T06:30:00Z",
  "robot_id": null,
  "metric_name": "decision_count",
  "actual_value": 47.0,
  "forecast_value": 12.3,
  "lower_bound": 5.1,
  "upper_bound": 19.5,
  "severity": "HIGH",
  "context": "Decision rate spiked to 47 (expected 12.3, upper bound 19.5)"
}
```

---

### Stage 3: AI Explanation Generation (Flink SQL + Gemini)

The third stage enriches raw anomaly alerts with **natural language explanations** using Google's Gemini model via Vertex AI—all within the Flink SQL environment.

#### Vertex AI Connection

```sql
CREATE CONNECTION gemini_connection
WITH (
    'type' = 'vertexai',
    'endpoint' = 'https://us-central1-aiplatform.googleapis.com/v1/projects/${PROJECT}/locations/us-central1/publishers/google/models/gemini-1.5-flash:generateContent',
    'service-account-key' = '${GCP_SERVICE_ACCOUNT_KEY}'
);

CREATE MODEL gemini_explainer
INPUT (prompt STRING)
OUTPUT (explanation STRING)
WITH (
    'provider' = 'vertexai',
    'vertexai.connection' = 'gemini_connection',
    'task' = 'text-generation'
);
```

#### Real-Time Enrichment Pipeline

```sql
INSERT INTO anomaly_alerts_enriched
SELECT
    a.alert_id,
    a.alert_type,
    a.detected_at,
    a.robot_id,
    a.severity,
    a.context,
    g.explanation AS ai_explanation
FROM anomaly_alerts a,
LATERAL TABLE(
    ML_PREDICT(
        'gemini_explainer',
        CONCAT(
            'You are a warehouse safety analyst. ',
            'Explain this anomaly alert to an operator in 1-2 sentences. ',
            'Be concise and actionable. ',
            'Alert: ', a.alert_type,
            '. Details: ', a.context,
            '. Severity: ', a.severity
        )
    )
) AS g(explanation);
```

**Output Topic:** `anomaly.alerts.enriched`
```json
{
  "alert_id": "rrs-1735625400-robot-42",
  "alert_type": "REPEATED_ROBOT_STOP",
  "detected_at": "2025-12-31T06:30:00Z",
  "robot_id": "robot-42",
  "severity": "HIGH",
  "context": "robot-42 stopped 5 times in 30s. Reasons: CLOSE_PROXIMITY",
  "ai_explanation": "Robot-42 is repeatedly stopping due to close human proximity. Check if a worker is stationed in the robot's path or if there's congestion in that aisle. Consider temporarily rerouting the robot or clearing the area."
}
```

---

## Why This Architecture Matters

### 1. True Stream Processing
Unlike batch-based anomaly detection that runs hourly or daily, this pipeline detects anomalies **within seconds** of the underlying pattern emerging. The ARIMA model is continuously updated with each new window.

### 2. AI at the Edge of the Stream
Gemini explanations are generated **inline with the data flow**, not as a separate post-processing step. This means operators see human-readable context immediately when an alert appears.

### 3. Confluent-Native ML
Both `ML_DETECT_ANOMALIES` and `ML_PREDICT` are first-class Flink SQL functions. No external ML infrastructure is needed—the entire pipeline runs within Confluent Cloud.

### 4. Composable and Extensible
Each stage writes to a Kafka topic, enabling:
- Multiple consumers (UI, mobile alerts, SIEM integration)
- Replay and debugging via topic retention
- Easy addition of new anomaly types or enrichment models

---

## Latency Characteristics

| Stage | Typical Latency |
|-------|-----------------|
| Telemetry → Decision | 50-100ms |
| Decision → Anomaly Detection | 10 seconds (window boundary) |
| Anomaly → AI Explanation | 200-500ms (Gemini API) |
| **Total: Telemetry → Explained Alert** | **~11 seconds** |

---

## Production Deployment

The pipeline is deployed across two environments:

| Component | Local Development | Production |
|-----------|-------------------|------------|
| Kafka | Docker (Confluent Platform) | Confluent Cloud |
| Flink SQL | Local Flink | Confluent Cloud Flink |
| Stream Processor | Docker container | Google Cloud Run |
| Gemini | Direct API | Vertex AI |

Topic naming uses prefixes (`local.` vs `prod.`) to isolate environments while sharing the same schema.

---

## Summary for Judges

**What we built:** A real-time AI alerting system that:
1. Processes warehouse telemetry at 10Hz per robot
2. Makes safety decisions using risk scoring
3. Detects statistical anomalies using Confluent's ML_DETECT_ANOMALIES
4. Generates natural language explanations using Gemini via ML_PREDICT
5. Delivers actionable alerts to operators in seconds

**Confluent integration depth:**
- QuixStreams for Python stream processing
- Flink SQL for windowed aggregation and anomaly detection
- Built-in ML functions (ML_DETECT_ANOMALIES, ML_PREDICT)
- Kafka topics as the universal data backbone
- Schema Registry for type-safe event contracts

**Google Cloud integration:**
- Vertex AI for Gemini model hosting
- Cloud Run for containerized services
- Firebase Hosting for the control center UI

This is not a demo where Confluent and Google Cloud are used separately—**they work together at every stage of the pipeline**, from ingestion through anomaly detection to AI-powered explanation generation.
