FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for confluent-kafka
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    librdkafka-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy and install dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir .

# Copy source
COPY src/ src/

# Run the simulator (PORT env var set by Cloud Run, default 8000 for local)
ENV PORT=8000
CMD uvicorn src.main:app --host 0.0.0.0 --port $PORT
