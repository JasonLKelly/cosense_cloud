-- ============================================================================
-- CoSense Cloud: Flink SQL Source Tables
-- ============================================================================
-- These tables connect Flink to Kafka topics in Confluent Cloud.
-- Run these statements first to establish the data sources.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Source: coordination.decisions
-- Decisions emitted by the stream processor (STOP, SLOW, REROUTE)
-- ----------------------------------------------------------------------------
CREATE TABLE coordination_decisions (
    decision_id STRING,
    robot_id STRING,
    `timestamp` BIGINT,
    zone_id STRING,
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
    'topic' = 'coordination.decisions',
    'properties.bootstrap.servers' = '${KAFKA_BROKERS}',
    'properties.group.id' = 'flink-anomaly-detection',
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
    zone_id STRING,
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
    'topic' = 'robot.telemetry',
    'properties.bootstrap.servers' = '${KAFKA_BROKERS}',
    'properties.group.id' = 'flink-anomaly-detection',
    'scan.startup.mode' = 'latest-offset',
    'format' = 'json'
);

-- ----------------------------------------------------------------------------
-- Source: zone.context
-- Zone-level environmental conditions
-- ----------------------------------------------------------------------------
CREATE TABLE zone_context (
    zone_id STRING,
    `timestamp` BIGINT,
    visibility STRING,
    congestion_level DOUBLE,
    robot_count INT,
    human_count INT,
    connectivity STRING,
    -- Event time
    event_time AS TO_TIMESTAMP_LTZ(`timestamp`, 3),
    WATERMARK FOR event_time AS event_time - INTERVAL '5' SECOND
) WITH (
    'connector' = 'kafka',
    'topic' = 'zone.context',
    'properties.bootstrap.servers' = '${KAFKA_BROKERS}',
    'properties.group.id' = 'flink-anomaly-detection',
    'scan.startup.mode' = 'latest-offset',
    'format' = 'json'
);
