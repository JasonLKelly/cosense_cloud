"""Simulator configuration."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Simulator settings from environment."""

    # Kafka connection (supports all three modes)
    kafka_brokers: str = "broker:29092"

    # Confluent Cloud / SASL auth (optional - leave empty for local)
    kafka_api_key: str = ""
    kafka_api_secret: str = ""
    kafka_security_protocol: str = ""  # SASL_SSL for Confluent Cloud
    kafka_sasl_mechanism: str = ""  # PLAIN for Confluent Cloud

    # Schema Registry (optional)
    schema_registry_url: str = ""
    schema_registry_api_key: str = ""
    schema_registry_api_secret: str = ""

    # Simulation
    tick_rate_hz: float = 10.0
    zone_id: str = "zone-c"

    # World size (meters)
    world_width: float = 50.0
    world_height: float = 30.0

    # Initial entities
    robot_count: int = 2
    human_count: int = 2

    # Random seed (0 = random)
    seed: int = 0

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
