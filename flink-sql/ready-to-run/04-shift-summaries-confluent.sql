-- ============================================================================
-- CoSense Cloud: Shift Summary Pipeline for Confluent Cloud Flink
-- ============================================================================
-- Run each statement separately in the Flink SQL shell.
-- Prerequisites: gemini-connection must exist (already confirmed)
-- ============================================================================

-- STEP 1: Create the Gemini summarizer model
-- Uses the existing gemini-connection

CREATE MODEL `cluster_0`.`gemini_summarizer`
INPUT (prompt STRING)
OUTPUT (response STRING)
WITH (
    'provider' = 'googleai',
    'googleai.connection' = 'gemini-connection',
    'googleai.model' = 'gemini-2.0-flash',
    'googleai.system_instruction' = 'You are a warehouse safety analyst. Provide concise, actionable summaries.'
);

-- ============================================================================

-- STEP 2: Create the 5-minute window aggregation view
-- Uses heuristic classification (NORMAL, HUMAN_FACTOR, EQUIPMENT, ENVIRONMENTAL)

CREATE VIEW `cluster_0`.`local_shift_window_classified` AS
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
    CASE
        WHEN COUNT(CASE WHEN primary_reason = 'SENSOR_DISAGREEMENT' THEN 1 END) >= 3 THEN 'EQUIPMENT'
        WHEN COUNT(CASE WHEN `action` = 'STOP' THEN 1 END) >= 4 AND COUNT(*) >= 15 THEN 'HUMAN_FACTOR'
        WHEN COUNT(CASE WHEN `action` = 'SLOW' THEN 1 END) >= 10
             AND COUNT(CASE WHEN `action` = 'SLOW' THEN 1 END) > COUNT(CASE WHEN `action` = 'STOP' THEN 1 END) * 3 THEN 'ENVIRONMENTAL'
        WHEN COUNT(*) <= 14 AND COUNT(CASE WHEN `action` = 'STOP' THEN 1 END) <= 2 THEN 'NORMAL'
        ELSE 'NORMAL'
    END AS category,
    CASE
        WHEN COUNT(CASE WHEN primary_reason = 'SENSOR_DISAGREEMENT' THEN 1 END) >= 3 THEN 0.85
        WHEN COUNT(CASE WHEN `action` = 'STOP' THEN 1 END) >= 4 AND COUNT(*) >= 15 THEN 0.80
        WHEN COUNT(CASE WHEN `action` = 'SLOW' THEN 1 END) >= 10 THEN 0.75
        ELSE 0.90
    END AS category_confidence
FROM TABLE(
    TUMBLE(TABLE `local.coordination.decisions`, DESCRIPTOR($rowtime), INTERVAL '5' MINUTE)
)
GROUP BY window_start, window_end;

-- ============================================================================

-- STEP 3: Create the INSERT job with Gemini summarization
-- This will create the local.shift.summaries topic and emit summaries

INSERT INTO `local.shift.summaries`
SELECT
    CONCAT('ss-', CAST(UNIX_TIMESTAMP(CAST(window_end AS TIMESTAMP)) AS STRING)) AS summary_id,
    window_start,
    window_end,
    decision_count,
    stop_count,
    slow_count,
    sensor_disagreement_count,
    category,
    category_confidence,
    context_summary,
    g.response AS ai_summary
FROM `cluster_0`.`local_shift_window_classified`,
LATERAL TABLE(
    ML_PREDICT(
        'gemini_summarizer',
        CONCAT(
            'Summarize this 5-minute warehouse shift in 2-3 sentences. Focus on actionable insights. ',
            'Classification: ', category, ' (', CAST(CAST(category_confidence * 100 AS INT) AS STRING), '% confidence). ',
            'Decisions: ', CAST(decision_count AS STRING), ' total (',
            CAST(stop_count AS STRING), ' stops, ',
            CAST(slow_count AS STRING), ' slows). ',
            'Avg risk: ', CAST(ROUND(avg_risk_score, 2) AS STRING), ', max: ', CAST(ROUND(max_risk_score, 2) AS STRING), '. ',
            'Details: ', COALESCE(SUBSTRING(context_summary, 1, 500), 'No specific incidents')
        )
    )
) AS g(response)
WHERE decision_count > 0;
