-- ============================================================================
-- CoSense Cloud: Flink SQL Source Tables
-- ============================================================================
-- These tables connect Flink to Kafka topics in Confluent Cloud.
-- Run these statements first to establish the data sources.
--
-- ENVIRONMENT VARIABLES (replace before running):
--   ${KAFKA_BROKERS}       - Confluent Cloud bootstrap server
--   ${KAFKA_API_KEY}       - Confluent Cloud API key
--   ${KAFKA_API_SECRET}    - Confluent Cloud API secret
--   ${KAFKA_TOPIC_PREFIX}  - Topic prefix (e.g., "local" or "prod")
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Source: coordination.decisions
-- Decisions emitted by the stream processor (STOP, SLOW, REROUTE)
-- ----------------------------------------------------------------------------
CREATE TABLE coordination_decisions (
    decision_id STRING,
    robot_id STRING,
    `timestamp` BIGINT,
    `action` STRING,
    reason_codes ARRAY<STRING>,
    primary_reason STRING,
    risk_score DOUBLE,
    nearest_human_distance DOUBLE,
    triggering_event STRING,
    summary STRING,
    -- Event time from the message timestamp
    event_time AS TO_TIMESTAMP_LTZ(`timestamp`, 3),
    -- Watermark allows 5 seconds of late data
    WATERMARK FOR event_time AS event_time - INTERVAL '5' SECOND
) WITH (
    'connector' = 'kafka',
    'topic' = '${KAFKA_TOPIC_PREFIX}.coordination.decisions',
    'properties.bootstrap.servers' = '${KAFKA_BROKERS}',
    'properties.group.id' = 'flink-anomaly-detection',
    'properties.security.protocol' = 'SASL_SSL',
    'properties.sasl.mechanism' = 'PLAIN',
    'properties.sasl.jaas.config' = 'org.apache.kafka.common.security.plain.PlainLoginModule required username="${KAFKA_API_KEY}" password="${KAFKA_API_SECRET}";',
    'scan.startup.mode' = 'latest-offset',
    'format' = 'json',
    'json.fail-on-missing-field' = 'false',
    'json.ignore-parse-errors' = 'true'
);

-- ----------------------------------------------------------------------------
-- Source: robot.telemetry
-- Real-time robot position and sensor data
-- ----------------------------------------------------------------------------
CREATE TABLE robot_telemetry (
    robot_id STRING,
    `timestamp` BIGINT,
    x DOUBLE,
    y DOUBLE,
    velocity DOUBLE,
    heading DOUBLE,
    motion_state STRING,
    ultrasonic_distance DOUBLE,
    ble_rssi INT,
    destination STRING,
    -- Event time
    event_time AS TO_TIMESTAMP_LTZ(`timestamp`, 3),
    WATERMARK FOR event_time AS event_time - INTERVAL '5' SECOND
) WITH (
    'connector' = 'kafka',
    'topic' = '${KAFKA_TOPIC_PREFIX}.robot.telemetry',
    'properties.bootstrap.servers' = '${KAFKA_BROKERS}',
    'properties.group.id' = 'flink-anomaly-detection',
    'properties.security.protocol' = 'SASL_SSL',
    'properties.sasl.mechanism' = 'PLAIN',
    'properties.sasl.jaas.config' = 'org.apache.kafka.common.security.plain.PlainLoginModule required username="${KAFKA_API_KEY}" password="${KAFKA_API_SECRET}";',
    'scan.startup.mode' = 'latest-offset',
    'format' = 'json'
);

