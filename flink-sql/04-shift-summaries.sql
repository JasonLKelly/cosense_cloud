-- ============================================================================
-- CoSense Cloud: Shift Summary Pipeline
-- ============================================================================
-- Uses ML_PREDICT with both AutoML (classification) and Gemini (summarization)
-- to generate AI-powered 5-minute shift summaries.
--
-- Pipeline:
--   1. 5-minute TUMBLE window aggregates coordination decisions
--   2. AutoML classifier categorizes the window (EQUIPMENT, ENVIRONMENTAL, etc.)
--   3. Gemini generates a natural language summary including the classification
--
-- ENVIRONMENT VARIABLES (replace before running):
--   ${KAFKA_BROKERS}              - Confluent Cloud bootstrap server
--   ${KAFKA_API_KEY}              - Confluent Cloud API key
--   ${KAFKA_API_SECRET}           - Confluent Cloud API secret
--   ${KAFKA_TOPIC_PREFIX}         - Topic prefix (e.g., "local" or "prod")
--   ${GOOGLE_CLOUD_LOCATION}      - GCP region (e.g., "us-central1")
--   ${GOOGLE_CLOUD_PROJECT}       - GCP project ID
--   ${GCP_SERVICE_ACCOUNT_KEY}    - GCP service account key JSON (escaped)
--   ${AUTOML_ENDPOINT_ID}         - Vertex AI AutoML endpoint ID
-- ============================================================================

-- ============================================================================
-- Connection: AutoML Classifier (mock or real)
-- For testing: uses mock-classifier Cloud Run service
-- For production: replace with real Vertex AI AutoML endpoint
-- ============================================================================
-- MOCK ENDPOINT (for testing):
--   https://mock-classifier-552194364406.us-central1.run.app
-- REAL ENDPOINT (after AutoML training completes):
--   https://${GOOGLE_CLOUD_LOCATION}-aiplatform.googleapis.com/v1/projects/${GOOGLE_CLOUD_PROJECT}/locations/${GOOGLE_CLOUD_LOCATION}/endpoints/${AUTOML_ENDPOINT_ID}:predict
-- ============================================================================
CREATE CONNECTION vertex_automl_conn
WITH (
    'type' = 'vertexai',
    'endpoint' = 'https://mock-classifier-552194364406.us-central1.run.app/v1/projects/${GOOGLE_CLOUD_PROJECT}/locations/${GOOGLE_CLOUD_LOCATION}/endpoints/mock:predict',
    'service-account-key' = '${GCP_SERVICE_ACCOUNT_KEY}'
);

-- ============================================================================
-- Model: AutoML Incident Classifier
-- Categorizes 5-minute windows into incident types based on decision metrics
-- Output categories: EQUIPMENT, ENVIRONMENTAL, HUMAN_FACTOR, NORMAL
-- ============================================================================
CREATE MODEL incident_classifier
INPUT (decision_count DOUBLE, stop_count DOUBLE, slow_count DOUBLE, sensor_disagreement_count DOUBLE)
OUTPUT (category STRING, confidence DOUBLE)
WITH (
    'provider' = 'vertexai',
    'vertexai.connection' = 'vertex_automl_conn'
);

-- ============================================================================
-- Model: Gemini Summarizer
-- Generates natural language summaries for shift supervisors
-- Reuses gemini_connection from 03-gemini-enrichment.sql
-- ============================================================================
CREATE MODEL gemini_summarizer
INPUT (prompt STRING)
OUTPUT (summary STRING)
WITH (
    'provider' = 'vertexai',
    'vertexai.connection' = 'gemini_connection',
    'task' = 'text-generation'
);

-- ============================================================================
-- Sink: shift.summaries
-- AI-generated shift summaries with classification and narrative
-- ============================================================================
CREATE TABLE shift_summaries (
    summary_id STRING,
    window_start TIMESTAMP(3),
    window_end TIMESTAMP(3),
    decision_count INT,
    stop_count INT,
    slow_count INT,
    sensor_disagreement_count INT,
    category STRING,
    category_confidence DOUBLE,
    context_summary STRING,
    ai_summary STRING,
    PRIMARY KEY (summary_id) NOT ENFORCED
) WITH (
    'connector' = 'kafka',
    'topic' = '${KAFKA_TOPIC_PREFIX}.shift.summaries',
    'properties.bootstrap.servers' = '${KAFKA_BROKERS}',
    'properties.security.protocol' = 'SASL_SSL',
    'properties.sasl.mechanism' = 'PLAIN',
    'properties.sasl.jaas.config' = 'org.apache.kafka.common.security.plain.PlainLoginModule required username="${KAFKA_API_KEY}" password="${KAFKA_API_SECRET}";',
    'format' = 'json',
    'key.format' = 'raw',
    'key.fields' = 'summary_id'
);

-- ============================================================================
-- View: 5-minute window aggregation
-- Aggregates coordination decisions into summary metrics
-- ============================================================================
CREATE VIEW shift_window_aggregates AS
SELECT
    window_start,
    window_end,
    COUNT(*) AS decision_count,
    COUNT(CASE WHEN `action` = 'STOP' THEN 1 END) AS stop_count,
    COUNT(CASE WHEN `action` = 'SLOW' THEN 1 END) AS slow_count,
    COUNT(CASE WHEN primary_reason = 'SENSOR_DISAGREEMENT' THEN 1 END) AS sensor_disagreement_count,
    AVG(risk_score) AS avg_risk_score,
    MAX(risk_score) AS max_risk_score,
    LISTAGG(
        CONCAT(robot_id, ': ', `action`, ' (', primary_reason, ')'),
        ' | '
    ) AS context_summary
FROM TABLE(
    TUMBLE(TABLE coordination_decisions, DESCRIPTOR(event_time), INTERVAL '5' MINUTE)
)
GROUP BY window_start, window_end;

-- ============================================================================
-- View: Classified windows (AutoML)
-- Adds incident classification to each 5-minute window
-- ============================================================================
CREATE VIEW shift_window_classified AS
SELECT
    w.*,
    c.category,
    c.confidence AS category_confidence
FROM shift_window_aggregates w,
LATERAL TABLE(
    ML_PREDICT(
        'incident_classifier',
        CAST(w.decision_count AS DOUBLE),
        CAST(w.stop_count AS DOUBLE),
        CAST(w.slow_count AS DOUBLE),
        CAST(w.sensor_disagreement_count AS DOUBLE)
    )
) AS c(category, confidence);

-- ============================================================================
-- Insert: Final summaries with classification + Gemini narrative
-- Only emits when there were decisions in the window
-- ============================================================================
INSERT INTO shift_summaries
SELECT
    CONCAT('ss-', CAST(UNIX_TIMESTAMP(window_end) AS STRING)) AS summary_id,
    window_start,
    window_end,
    CAST(decision_count AS INT),
    CAST(stop_count AS INT),
    CAST(slow_count AS INT),
    CAST(sensor_disagreement_count AS INT),
    category,
    category_confidence,
    context_summary,
    g.summary AS ai_summary
FROM shift_window_classified,
LATERAL TABLE(
    ML_PREDICT(
        'gemini_summarizer',
        CONCAT(
            'You are a warehouse safety analyst. Summarize this 5-minute shift for a supervisor in 2-3 sentences. ',
            'Focus on actionable insights. ',
            'Classification: ', category, ' (', CAST(ROUND(category_confidence * 100, 0) AS STRING), '% confidence). ',
            'Decisions: ', CAST(decision_count AS STRING), ' total (',
            CAST(stop_count AS STRING), ' stops, ',
            CAST(slow_count AS STRING), ' slows). ',
            'Avg risk: ', CAST(ROUND(avg_risk_score, 2) AS STRING), ', max: ', CAST(ROUND(max_risk_score, 2) AS STRING), '. ',
            'Details: ', COALESCE(SUBSTRING(context_summary, 1, 500), 'No specific incidents')
        )
    )
) AS g(summary)
WHERE decision_count > 0;
