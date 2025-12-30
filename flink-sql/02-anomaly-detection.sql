-- ============================================================================
-- CoSense Cloud: Anomaly Detection Pipeline
-- ============================================================================
-- Uses ML_DETECT_ANOMALIES to identify unusual patterns in the decision stream.
-- Detects: decision rate spikes, repeated robot stops, sensor disagreements
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Sink: anomaly.alerts
-- Detected anomalies are written here for UI consumption
-- ----------------------------------------------------------------------------
CREATE TABLE anomaly_alerts (
    alert_id STRING,
    alert_type STRING,
    detected_at TIMESTAMP(3),
    zone_id STRING,
    robot_id STRING,
    metric_name STRING,
    actual_value DOUBLE,
    forecast_value DOUBLE,
    lower_bound DOUBLE,
    upper_bound DOUBLE,
    severity STRING,
    context STRING,
    PRIMARY KEY (alert_id) NOT ENFORCED
) WITH (
    'connector' = 'kafka',
    'topic' = 'anomaly.alerts',
    'properties.bootstrap.servers' = '${KAFKA_BROKERS}',
    'format' = 'json',
    'key.format' = 'raw',
    'key.fields' = 'alert_id'
);

-- ----------------------------------------------------------------------------
-- View: Decision Rate per 10-second Window
-- Aggregates decisions to detect rate spikes
-- ----------------------------------------------------------------------------
CREATE VIEW decision_rate_windowed AS
SELECT
    window_start,
    window_end,
    window_time,
    zone_id,
    COUNT(*) AS decision_count,
    COUNT(CASE WHEN `action` = 'STOP' THEN 1 END) AS stop_count,
    COUNT(CASE WHEN `action` = 'SLOW' THEN 1 END) AS slow_count,
    COUNT(CASE WHEN primary_reason = 'SENSOR_DISAGREEMENT' THEN 1 END) AS sensor_disagreement_count,
    AVG(risk_score) AS avg_risk_score,
    MAX(risk_score) AS max_risk_score
FROM TABLE(
    TUMBLE(TABLE coordination_decisions, DESCRIPTOR(event_time), INTERVAL '10' SECOND)
)
GROUP BY window_start, window_end, window_time, zone_id;

-- ----------------------------------------------------------------------------
-- View: Anomaly Detection on Decision Rate
-- Detects unusual spikes in decision frequency
-- ----------------------------------------------------------------------------
CREATE VIEW decision_rate_anomalies AS
SELECT
    window_time,
    zone_id,
    decision_count,
    stop_count,
    ML_DETECT_ANOMALIES(
        CAST(decision_count AS DOUBLE),
        window_time,
        JSON_OBJECT(
            'minTrainingSize' VALUE 6,        -- 1 minute of 10s windows
            'maxTrainingSize' VALUE 60,       -- 10 minutes of history
            'confidencePercentage' VALUE 95.0,
            'enableStl' VALUE false           -- No seasonality expected
        )
    ) OVER (
        ORDER BY window_time
        RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS anomaly_result
FROM decision_rate_windowed;

-- ----------------------------------------------------------------------------
-- View: Robot Stop Frequency (per robot, per minute)
-- Detects robots that are stopping repeatedly
-- ----------------------------------------------------------------------------
CREATE VIEW robot_stop_frequency AS
SELECT
    window_start,
    window_end,
    window_time,
    robot_id,
    zone_id,
    COUNT(*) AS stop_count,
    LISTAGG(primary_reason, ', ') AS reasons
FROM TABLE(
    TUMBLE(TABLE coordination_decisions, DESCRIPTOR(event_time), INTERVAL '30' SECOND)
)
WHERE `action` = 'STOP'
GROUP BY window_start, window_end, window_time, robot_id, zone_id
HAVING COUNT(*) >= 2;  -- Robot stopped 2+ times in 30 seconds

-- ----------------------------------------------------------------------------
-- Insert: Decision Rate Anomaly Alerts
-- When decision rate is anomalous, emit an alert
-- ----------------------------------------------------------------------------
INSERT INTO anomaly_alerts
SELECT
    CONCAT('dra-', CAST(UNIX_TIMESTAMP(window_time) AS STRING), '-', zone_id) AS alert_id,
    'DECISION_RATE_SPIKE' AS alert_type,
    window_time AS detected_at,
    zone_id,
    CAST(NULL AS STRING) AS robot_id,
    'decision_count' AS metric_name,
    CAST(decision_count AS DOUBLE) AS actual_value,
    anomaly_result.forecast_value,
    anomaly_result.lower_bound,
    anomaly_result.upper_bound,
    CASE
        WHEN decision_count > anomaly_result.upper_bound * 1.5 THEN 'HIGH'
        ELSE 'MEDIUM'
    END AS severity,
    CONCAT('Decision rate spiked to ', CAST(decision_count AS STRING),
           ' (expected ', CAST(ROUND(anomaly_result.forecast_value, 1) AS STRING),
           ', upper bound ', CAST(ROUND(anomaly_result.upper_bound, 1) AS STRING), ')')
    AS context
FROM decision_rate_anomalies
WHERE anomaly_result.is_anomaly = TRUE
  AND anomaly_result.forecast_value IS NOT NULL;

-- ----------------------------------------------------------------------------
-- Insert: Repeated Robot Stop Alerts
-- When a robot stops multiple times in 30 seconds
-- ----------------------------------------------------------------------------
INSERT INTO anomaly_alerts
SELECT
    CONCAT('rrs-', CAST(UNIX_TIMESTAMP(window_time) AS STRING), '-', robot_id) AS alert_id,
    'REPEATED_ROBOT_STOP' AS alert_type,
    window_time AS detected_at,
    zone_id,
    robot_id,
    'stop_count_30s' AS metric_name,
    CAST(stop_count AS DOUBLE) AS actual_value,
    CAST(1.0 AS DOUBLE) AS forecast_value,  -- Expected: 0-1 stops per 30s
    CAST(0.0 AS DOUBLE) AS lower_bound,
    CAST(1.0 AS DOUBLE) AS upper_bound,
    CASE
        WHEN stop_count >= 3 THEN 'HIGH'
        ELSE 'MEDIUM'
    END AS severity,
    CONCAT(robot_id, ' stopped ', CAST(stop_count AS STRING),
           ' times in 30s. Reasons: ', reasons)
    AS context
FROM robot_stop_frequency;

-- ----------------------------------------------------------------------------
-- Insert: Sensor Disagreement Alerts
-- When sensor disagreements are detected
-- ----------------------------------------------------------------------------
INSERT INTO anomaly_alerts
SELECT
    CONCAT('sd-', CAST(UNIX_TIMESTAMP(window_time) AS STRING), '-', zone_id) AS alert_id,
    'SENSOR_DISAGREEMENT_SPIKE' AS alert_type,
    window_time AS detected_at,
    zone_id,
    CAST(NULL AS STRING) AS robot_id,
    'sensor_disagreement_count' AS metric_name,
    CAST(sensor_disagreement_count AS DOUBLE) AS actual_value,
    CAST(0.0 AS DOUBLE) AS forecast_value,
    CAST(0.0 AS DOUBLE) AS lower_bound,
    CAST(1.0 AS DOUBLE) AS upper_bound,
    'HIGH' AS severity,
    CONCAT(CAST(sensor_disagreement_count AS STRING),
           ' sensor disagreements detected in 10s window')
    AS context
FROM decision_rate_windowed
WHERE sensor_disagreement_count >= 2;
