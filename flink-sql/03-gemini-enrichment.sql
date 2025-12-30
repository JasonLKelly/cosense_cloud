-- ============================================================================
-- CoSense Cloud: Gemini AI Enrichment
-- ============================================================================
-- Uses ML_PREDICT with Vertex AI to generate natural language explanations
-- for detected anomalies. This creates the "AI on data in motion" story.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Connection: Vertex AI / Gemini
-- Requires GCP service account with aiplatform.endpoints.predict permission
-- ----------------------------------------------------------------------------
CREATE CONNECTION gemini_connection
WITH (
    'type' = 'vertexai',
    'endpoint' = 'https://${GCP_REGION}-aiplatform.googleapis.com/v1/projects/${GCP_PROJECT_ID}/locations/${GCP_REGION}/publishers/google/models/gemini-1.5-flash:generateContent',
    'service-account-key' = '${GCP_SERVICE_ACCOUNT_KEY_JSON}'
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
    'topic' = 'anomaly.alerts.enriched',
    'properties.bootstrap.servers' = '${KAFKA_BROKERS}',
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
