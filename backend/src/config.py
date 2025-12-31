"""Backend configuration."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Backend settings from environment."""

    # Kafka connection (supports all three modes)
    kafka_brokers: str = "broker:29092"
    consumer_group: str = "cosense-backend"

    # Confluent Cloud / SASL auth (optional - leave empty for local)
    kafka_api_key: str = ""
    kafka_api_secret: str = ""
    kafka_security_protocol: str = ""  # SASL_SSL for Confluent Cloud
    kafka_sasl_mechanism: str = ""  # PLAIN for Confluent Cloud

    # Schema Registry (optional)
    schema_registry_url: str = ""
    schema_registry_api_key: str = ""
    schema_registry_api_secret: str = ""

    # Topic prefix for namespacing (e.g., "local", "prod")
    kafka_topic_prefix: str = ""

    # Topics to consume (base names)
    coordination_state_topic: str = "coordination.state"
    coordination_decisions_topic: str = "coordination.decisions"
    anomaly_alerts_topic: str = "anomaly.alerts"  # Raw alerts from Flink ML_DETECT_ANOMALIES
    shift_summaries_topic: str = "shift.summaries"  # AI-generated shift summaries from Flink

    # Simulator service (for forwarding commands)
    simulator_url: str = "http://simulator:8000"

    # Google Cloud / Gemini
    google_cloud_project: str = ""
    google_cloud_location: str = "us-central1"
    gemini_model: str = "gemini-2.0-flash"
    # Set to False to use API key auth instead of Vertex AI
    use_vertex_ai: bool = True
    # Only needed if use_vertex_ai is False
    google_api_key: str = ""

    # State buffer
    max_decisions_buffer: int = 100
    max_state_buffer: int = 50
    max_anomalies_buffer: int = 50
    max_summaries_buffer: int = 10  # Keep last 10 shift summaries

    class Config:
        env_prefix = ""

    def topic(self, name: str) -> str:
        """Get prefixed topic name."""
        if self.kafka_topic_prefix:
            return f"{self.kafka_topic_prefix}.{name}"
        return name

    @property
    def prefixed_consumer_group(self) -> str:
        """Get consumer group with prefix."""
        if self.kafka_topic_prefix:
            return f"{self.kafka_topic_prefix}-{self.consumer_group}"
        return self.consumer_group

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
