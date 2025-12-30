# Flink AI Pipeline: Anomaly Detection + Gemini Enrichment

This document describes the Confluent Cloud Flink SQL pipeline that performs real-time anomaly detection and AI-powered explanation generation.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        CONFLUENT CLOUD                                       │
│                                                                              │
│  ┌──────────────────┐                                                        │
│  │ coordination.    │                                                        │
│  │ decisions        │                                                        │
│  └────────┬─────────┘                                                        │
│           │                                                                  │
│           ▼                                                                  │
│  ┌────────────────────────────────────────┐                                 │
│  │         FLINK SQL                       │                                 │
│  │  ┌──────────────────────────────────┐  │                                 │
│  │  │  10-second TUMBLE window         │  │                                 │
│  │  │  - decision_count                │  │                                 │
│  │  │  - stop_count                    │  │                                 │
│  │  │  - sensor_disagreement_count     │  │                                 │
│  │  └──────────────┬───────────────────┘  │                                 │
│  │                 │                       │                                 │
│  │                 ▼                       │                                 │
│  │  ┌──────────────────────────────────┐  │                                 │
│  │  │  ML_DETECT_ANOMALIES (ARIMA)     │  │                                 │
│  │  │  - Detects rate spikes           │  │                                 │
│  │  │  - Returns is_anomaly boolean    │  │                                 │
│  │  └──────────────┬───────────────────┘  │                                 │
│  │                 │                       │                                 │
│  │                 ▼                       │                                 │
│  │  ┌──────────────────────────────────┐  │      ┌─────────────────────┐   │
│  │  │  ML_PREDICT (Gemini via Vertex)  │◄─┼──────│  Google Vertex AI   │   │
│  │  │  - Generates explanation         │  │      │  (Gemini 1.5 Flash) │   │
│  │  └──────────────┬───────────────────┘  │      └─────────────────────┘   │
│  └─────────────────┼──────────────────────┘                                 │
│                    │                                                         │
│                    ▼                                                         │
│  ┌──────────────────────────────────────┐                                   │
│  │  anomaly.alerts.enriched             │                                   │
│  │  (with AI explanation)               │                                   │
│  └──────────────────┬───────────────────┘                                   │
│                     │                                                        │
└─────────────────────┼────────────────────────────────────────────────────────┘
                      │
                      ▼
              ┌───────────────┐
              │  Control      │
              │  Center UI    │
              │  (React)      │
              └───────────────┘
```

## Anomaly Types Detected

| Alert Type | Trigger | Severity |
|------------|---------|----------|
| `DECISION_RATE_SPIKE` | Decision count exceeds ARIMA confidence bounds | MEDIUM/HIGH |
| `REPEATED_ROBOT_STOP` | Same robot stops 2+ times in 30 seconds | MEDIUM/HIGH |
| `SENSOR_DISAGREEMENT_SPIKE` | 2+ sensor disagreements in 10 seconds | HIGH |

## Flink SQL Files

| File | Purpose |
|------|---------|
| `01-source-tables.sql` | Kafka source table definitions |
| `02-anomaly-detection.sql` | ML_DETECT_ANOMALIES pipeline |
| `03-gemini-enrichment.sql` | ML_PREDICT for AI explanations |

## Setup Steps

### 1. Prerequisites

- Confluent Cloud account with Flink enabled
- GCP project with Vertex AI API enabled
- Service account with `aiplatform.endpoints.predict` permission

### 2. Create Kafka Topics

```bash
# In Confluent Cloud Console or CLI
confluent kafka topic create anomaly.alerts
confluent kafka topic create anomaly.alerts.enriched
```

### 3. Set Environment Variables

The SQL files use placeholders that must be replaced:

| Placeholder | Value |
|-------------|-------|
| `${KAFKA_BROKERS}` | Your Confluent Cloud bootstrap server |
| `${GCP_REGION}` | e.g., `us-central1` |
| `${GCP_PROJECT_ID}` | Your GCP project ID |
| `${GCP_SERVICE_ACCOUNT_KEY_JSON}` | Base64-encoded service account key |

### 4. Deploy to Flink

Run the SQL files in order via Confluent Cloud Console or CLI:

```bash
# Using Confluent CLI
confluent flink statement create --sql "$(cat flink-sql/01-source-tables.sql)"
confluent flink statement create --sql "$(cat flink-sql/02-anomaly-detection.sql)"
confluent flink statement create --sql "$(cat flink-sql/03-gemini-enrichment.sql)"
```

Or use the Confluent Cloud Flink SQL workspace UI.

## Output Schema

### anomaly.alerts

```json
{
  "alert_id": "dra-1703145600-zone-c",
  "alert_type": "DECISION_RATE_SPIKE",
  "detected_at": "2024-12-21T12:00:00Z",
  "zone_id": "zone-c",
  "robot_id": null,
  "metric_name": "decision_count",
  "actual_value": 15.0,
  "forecast_value": 5.2,
  "lower_bound": 2.1,
  "upper_bound": 8.3,
  "severity": "HIGH",
  "context": "Decision rate spiked to 15 (expected 5.2, upper bound 8.3)"
}
```

### anomaly.alerts.enriched

Same as above, plus:

```json
{
  "ai_explanation": "Zone C is experiencing an unusual surge in safety interventions. Check for environmental changes like reduced visibility or increased foot traffic that may be triggering multiple robot stops."
}
```

## Demo Impact

**Key talking points:**

1. "Anomaly detection happens IN the stream, not in a batch job after the fact"
2. "Flink's ML_DETECT_ANOMALIES uses ARIMA to learn normal patterns automatically"
3. "When an anomaly is detected, Gemini generates an explanation in real-time"
4. "This is true AI on data in motion—the full loop from detection to explanation happens in milliseconds"

## Billing Notes

- `ML_DETECT_ANOMALIES` is charged as part of Flink compute (CFUs)
- `ML_PREDICT` calls to Vertex AI are billed by Google Cloud
- For the hackathon demo, usage will be minimal
