-- ============================================================================
-- CoSense Cloud: Gemini AI Enrichment
-- ============================================================================
-- Uses ML_PREDICT with Vertex AI to generate natural language explanations
-- for detected anomalies. This creates the "AI on data in motion" story.
--
-- ENVIRONMENT VARIABLES (replace before running):
--   ${KAFKA_BROKERS}              - Confluent Cloud bootstrap server
--   ${KAFKA_API_KEY}              - Confluent Cloud API key
--   ${KAFKA_API_SECRET}           - Confluent Cloud API secret
--   ${KAFKA_TOPIC_PREFIX}         - Topic prefix (e.g., "local" or "prod")
--   ${GOOGLE_CLOUD_LOCATION}      - GCP region (e.g., "us-central1")
--   ${GOOGLE_CLOUD_PROJECT}       - GCP project ID
--   ${GCP_SERVICE_ACCOUNT_KEY}    - GCP service account key JSON (escaped)
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Connection: Vertex AI / Gemini
-- Requires GCP service account with aiplatform.endpoints.predict permission
-- ----------------------------------------------------------------------------
CREATE CONNECTION gemini_connection
WITH (
    'type' = 'vertexai',
    'endpoint' = 'https://${GOOGLE_CLOUD_LOCATION}-aiplatform.googleapis.com/v1/projects/${GOOGLE_CLOUD_PROJECT}/locations/${GOOGLE_CLOUD_LOCATION}/publishers/google/models/gemini-1.5-flash:generateContent',
    'service-account-key' = '${GCP_SERVICE_ACCOUNT_KEY}'
);

-- ----------------------------------------------------------------------------
-- Model: Gemini for Anomaly Explanation
-- Generates operator-friendly explanations for detected anomalies
-- ----------------------------------------------------------------------------
CREATE MODEL gemini_explainer
INPUT (prompt STRING)
OUTPUT (explanation STRING)
WITH (
    'provider' = 'vertexai',
    'vertexai.connection' = 'gemini_connection',
    'task' = 'text-generation'
);

-- ----------------------------------------------------------------------------
-- Sink: Enriched Anomaly Alerts with AI Explanations
-- ----------------------------------------------------------------------------
CREATE TABLE anomaly_alerts_enriched (
    alert_id STRING,
    alert_type STRING,
    detected_at TIMESTAMP(3),
    zone_id STRING,
    robot_id STRING,
    metric_name STRING,
    actual_value DOUBLE,
    forecast_value DOUBLE,
    severity STRING,
    context STRING,
    ai_explanation STRING,
    PRIMARY KEY (alert_id) NOT ENFORCED
) WITH (
    'connector' = 'kafka',
    'topic' = '${KAFKA_TOPIC_PREFIX}.anomaly.alerts.enriched',
    'properties.bootstrap.servers' = '${KAFKA_BROKERS}',
    'properties.security.protocol' = 'SASL_SSL',
    'properties.sasl.mechanism' = 'PLAIN',
    'properties.sasl.jaas.config' = 'org.apache.kafka.common.security.plain.PlainLoginModule required username="${KAFKA_API_KEY}" password="${KAFKA_API_SECRET}";',
    'format' = 'json',
    'key.format' = 'raw',
    'key.fields' = 'alert_id'
);

-- ----------------------------------------------------------------------------
-- Pipeline: Enrich Anomaly Alerts with Gemini Explanations
-- ----------------------------------------------------------------------------
INSERT INTO anomaly_alerts_enriched
SELECT
    a.alert_id,
    a.alert_type,
    a.detected_at,
    a.zone_id,
    a.robot_id,
    a.metric_name,
    a.actual_value,
    a.forecast_value,
    a.severity,
    a.context,
    g.explanation AS ai_explanation
FROM anomaly_alerts a,
LATERAL TABLE(
    ML_PREDICT(
        'gemini_explainer',
        CONCAT(
            'You are a warehouse safety analyst. Explain this anomaly alert to an operator in 1-2 sentences. ',
            'Be concise and actionable. Alert: ', a.alert_type,
            '. Details: ', a.context,
            '. Severity: ', a.severity,
            CASE WHEN a.robot_id IS NOT NULL
                THEN CONCAT('. Robot: ', a.robot_id)
                ELSE ''
            END,
            '. Zone: ', a.zone_id
        )
    )
) AS g(explanation);
