FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for confluent-kafka (used by quixstreams)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    librdkafka-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy and install dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir .

# Copy source
COPY src/ src/

# Run the stream processor
CMD ["python", "-m", "src.main"]
