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

    # Topics to consume
    coordination_state_topic: str = "coordination.state"
    coordination_decisions_topic: str = "coordination.decisions"
    zone_context_topic: str = "zone.context"

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
