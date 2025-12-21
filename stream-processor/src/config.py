"""Stream processor configuration."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Stream processor settings from environment."""

    # Kafka connection (supports all three modes)
    kafka_brokers: str = "broker:29092"
    consumer_group: str = "cosense-stream-processor"

    # Confluent Cloud / SASL auth (optional - leave empty for local)
    kafka_api_key: str = ""
    kafka_api_secret: str = ""
    kafka_security_protocol: str = ""  # SASL_SSL for Confluent Cloud
    kafka_sasl_mechanism: str = ""  # PLAIN for Confluent Cloud

    # Schema Registry (optional)
    schema_registry_url: str = ""
    schema_registry_api_key: str = ""
    schema_registry_api_secret: str = ""

    # Topics
    robot_telemetry_topic: str = "robot.telemetry"
    human_telemetry_topic: str = "human.telemetry"
    zone_context_topic: str = "zone.context"
    coordination_state_topic: str = "coordination.state"
    coordination_decisions_topic: str = "coordination.decisions"

    # Processing
    join_window_ms: int = 500
    state_emit_interval_ms: int = 200

    # Risk thresholds
    proximity_warning_m: float = 3.0
    proximity_critical_m: float = 1.5
    speed_warning_ms: float = 1.5
    congestion_warning: float = 0.6

    class Config:
        env_prefix = ""

    def get_kafka_config(self) -> dict:
        """Get Kafka producer/consumer config dict."""
        config = {
            "bootstrap.servers": self.kafka_brokers,
        }

        # Add SASL auth if configured (Confluent Cloud)
        if self.kafka_api_key and self.kafka_api_secret:
            config.update({
                "security.protocol": self.kafka_security_protocol or "SASL_SSL",
                "sasl.mechanism": self.kafka_sasl_mechanism or "PLAIN",
                "sasl.username": self.kafka_api_key,
                "sasl.password": self.kafka_api_secret,
            })

        return config


settings = Settings()
