-- ============================================================================
-- CoSense Cloud: Shift Summary Pipeline (Simplified - No AutoML)
-- ============================================================================
-- Generates AI-powered 5-minute shift summaries using Gemini only.
-- Classification is done via heuristics in the SQL until AutoML model is ready.
--
-- PREREQUISITES: Run these files first:
--   1. 01-source-tables.sql (creates coordination_decisions table)
--   2. 03-gemini-enrichment.sql (creates gemini_connection)
--
-- ENVIRONMENT VARIABLES (replace before running):
--   ${KAFKA_BROKERS}              - Confluent Cloud bootstrap server
--   ${KAFKA_API_KEY}              - Confluent Cloud API key
--   ${KAFKA_API_SECRET}           - Confluent Cloud API secret
--   ${KAFKA_TOPIC_PREFIX}         - Topic prefix (e.g., "local" or "prod")
-- ============================================================================

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
-- View: 5-minute window aggregation with heuristic classification
-- Classification logic matches the AutoML training data patterns
-- ============================================================================
CREATE VIEW shift_window_classified AS
SELECT
    window_start,
    window_end,
    CAST(COUNT(*) AS INT) AS decision_count,
    CAST(COUNT(CASE WHEN `action` = 'STOP' THEN 1 END) AS INT) AS stop_count,
    CAST(COUNT(CASE WHEN `action` = 'SLOW' THEN 1 END) AS INT) AS slow_count,
    CAST(COUNT(CASE WHEN primary_reason = 'SENSOR_DISAGREEMENT' THEN 1 END) AS INT) AS sensor_disagreement_count,
    AVG(risk_score) AS avg_risk_score,
    MAX(risk_score) AS max_risk_score,
    LISTAGG(
        CONCAT(robot_id, ': ', `action`, ' (', primary_reason, ')'),
        ' | '
    ) AS context_summary,
    -- Heuristic classification (matches AutoML training patterns)
    CASE
        WHEN COUNT(CASE WHEN primary_reason = 'SENSOR_DISAGREEMENT' THEN 1 END) >= 3 THEN 'EQUIPMENT'
        WHEN COUNT(CASE WHEN `action` = 'STOP' THEN 1 END) >= 4 AND COUNT(*) >= 15 THEN 'HUMAN_FACTOR'
        WHEN COUNT(CASE WHEN `action` = 'SLOW' THEN 1 END) >= 10
             AND COUNT(CASE WHEN `action` = 'SLOW' THEN 1 END) > COUNT(CASE WHEN `action` = 'STOP' THEN 1 END) * 3 THEN 'ENVIRONMENTAL'
        WHEN COUNT(*) <= 14 AND COUNT(CASE WHEN `action` = 'STOP' THEN 1 END) <= 2 THEN 'NORMAL'
        ELSE 'NORMAL'
    END AS category,
    -- Confidence based on how clearly the pattern matches
    CASE
        WHEN COUNT(CASE WHEN primary_reason = 'SENSOR_DISAGREEMENT' THEN 1 END) >= 3 THEN 0.85
        WHEN COUNT(CASE WHEN `action` = 'STOP' THEN 1 END) >= 4 AND COUNT(*) >= 15 THEN 0.80
        WHEN COUNT(CASE WHEN `action` = 'SLOW' THEN 1 END) >= 10 THEN 0.75
        ELSE 0.90
    END AS category_confidence
FROM TABLE(
    TUMBLE(TABLE coordination_decisions, DESCRIPTOR(event_time), INTERVAL '5' MINUTE)
)
GROUP BY window_start, window_end;

-- ============================================================================
-- Insert: Final summaries with Gemini narrative
-- Only emits when there were decisions in the window
-- ============================================================================
INSERT INTO shift_summaries
SELECT
    CONCAT('ss-', CAST(UNIX_TIMESTAMP(window_end) AS STRING)) AS summary_id,
    window_start,
    window_end,
    decision_count,
    stop_count,
    slow_count,
    sensor_disagreement_count,
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
            'Classification: ', category, ' (', CAST(CAST(category_confidence * 100 AS INT) AS STRING), '% confidence). ',
            'Decisions: ', CAST(decision_count AS STRING), ' total (',
            CAST(stop_count AS STRING), ' stops, ',
            CAST(slow_count AS STRING), ' slows). ',
            'Avg risk: ', CAST(ROUND(avg_risk_score, 2) AS STRING), ', max: ', CAST(ROUND(max_risk_score, 2) AS STRING), '. ',
            'Details: ', COALESCE(SUBSTRING(context_summary, 1, 500), 'No specific incidents')
        )
    )
) AS g(summary)
WHERE decision_count > 0;
