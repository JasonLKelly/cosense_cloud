-- ============================================================================
-- CoSense Cloud: Flink SQL Source Tables (READY TO RUN)
-- ============================================================================
-- Run this FIRST in Confluent Cloud Flink SQL workspace
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Source: coordination.decisions
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
    event_time AS TO_TIMESTAMP_LTZ(`timestamp`, 3),
    WATERMARK FOR event_time AS event_time - INTERVAL '5' SECOND
) WITH (
    'connector' = 'kafka',
    'topic' = 'local.coordination.decisions',
    'properties.bootstrap.servers' = 'pkc-619z3.us-east1.gcp.confluent.cloud:9092',
    'properties.group.id' = 'flink-anomaly-detection',
    'properties.security.protocol' = 'SASL_SSL',
    'properties.sasl.mechanism' = 'PLAIN',
    'properties.sasl.jaas.config' = 'org.apache.kafka.common.security.plain.PlainLoginModule required username="TUTX35KAYVRHCW37" password="cfltiHTAMyorxQ6E4xUw8SGupFt56QpGe6jDo0FMlF44NNC11GyNBVf8vNbmiAng";',
    'scan.startup.mode' = 'latest-offset',
    'format' = 'json',
    'json.fail-on-missing-field' = 'false',
    'json.ignore-parse-errors' = 'true'
);

-- ----------------------------------------------------------------------------
-- Source: robot.telemetry
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
    event_time AS TO_TIMESTAMP_LTZ(`timestamp`, 3),
    WATERMARK FOR event_time AS event_time - INTERVAL '5' SECOND
) WITH (
    'connector' = 'kafka',
    'topic' = 'local.robot.telemetry',
    'properties.bootstrap.servers' = 'pkc-619z3.us-east1.gcp.confluent.cloud:9092',
    'properties.group.id' = 'flink-anomaly-detection',
    'properties.security.protocol' = 'SASL_SSL',
    'properties.sasl.mechanism' = 'PLAIN',
    'properties.sasl.jaas.config' = 'org.apache.kafka.common.security.plain.PlainLoginModule required username="TUTX35KAYVRHCW37" password="cfltiHTAMyorxQ6E4xUw8SGupFt56QpGe6jDo0FMlF44NNC11GyNBVf8vNbmiAng";',
    'scan.startup.mode' = 'latest-offset',
    'format' = 'json'
);
