# CoSense Cloud
### Real-Time Human–Robot Coordination with Streaming AI and Edge-Aware Reasoning

CoSense Cloud is an open-source, cloud-native demonstration of **real-time human–robot coordination** in warehouse environments. It shows how streaming telemetry, edge-aware decision logic, and **LLM-based operator copilots** can work together to produce systems that are fast, explainable, and resilient.

This project was built for the **Google AI Partner Catalyst** and is designed to be:
- reproducible with a single command
- grounded in real system architecture
- focused on learning, teaching, and clarity over productization

---

## Core Idea

Modern robot fleets generate large volumes of telemetry, but operators often lack clear answers to simple questions like:

- *Why did this robot stop?*
- *What’s happening in this zone right now?*
- *Is this an isolated event or part of a pattern?*

CoSense Cloud addresses this by combining:
- **streaming data fusion** for real-time coordination decisions
- **structured LLM reasoning** for operator understanding
- **edge-aware assumptions**, even in a cloud-hosted demo

> Instead of relying on centralized coordination alone, CoSense demonstrates how perception, fusion, and reasoning can be distributed—while maintaining explainability and operational trust.

---

## Architecture Overview

CoSense Cloud is composed of four main parts:

1. **Headless Simulator (World Engine)**  
   Generates robots, humans, and zones in a warehouse-like environment and emits realistic telemetry as event streams.

2. **Streaming Fusion & Decision Engine**  
   Consumes telemetry, performs windowed joins and stateful aggregation, and emits coordination decisions such as **SLOW**, **STOP**, or **REROUTE**, along with structured reason codes.

3. **Operator Copilot (Vertex AI / Gemini)**  
   Uses **Gemini with structured outputs and guardrails** to answer operator questions by grounding responses in telemetry, decisions, and recent system state.

4. **Control Center UI**  
   A web-based operations view that renders robot and human positions, shows decisions in real time, and allows operators to ask questions in natural language.

All components run locally via Docker Compose and are containerized for a direct deployment path to **Google Cloud Run**.

---

## Google Cloud: Key Technical Angle

### Vertex AI / Gemini as an Operator Copilot (KEY)

Gemini is used **only for reasoning and explanation**, not for real-time control or safety decisions.

Specifically, Gemini:
- answers operator questions about robot behavior
- explains *why* decisions were made
- summarizes recent system behavior
- highlights contributing signals and conditions

All Gemini responses are:
- **schema-constrained** (structured JSON output)
- **grounded in telemetry** provided via tool calls
- **guarded against hallucination** by refusing to answer when data is insufficient

This makes Gemini suitable for operational use cases where **trust, auditability, and clarity** matter.

> Gemini transforms high-frequency telemetry into operator-grade situational understanding.

---

### Cloud Run as the Deployment Path

All services are containerized and run locally via Docker Compose.

The same containers can be deployed to **Google Cloud Run** with no architectural changes, providing:
- a realistic production path
- managed scaling and isolation
- cost-controlled execution

Local reproducibility and cloud deployment share the same artifacts.

---

## Streaming and Decision Logic

### Telemetry Streams
The simulator publishes events such as:
- robot position, velocity, and motion state
- ultrasonic proximity
- BLE-based human proximity
- zone-level congestion and visibility flags

### Decision Engine
The streaming processor:
- joins robot, human, and zone events in time windows
- computes a risk score per robot
- maps risk and context to actions
- emits **reason codes** explaining each decision

Example reason codes:
- `CLOSE_PROXIMITY`
- `HIGH_RELATIVE_SPEED`
- `LOW_VISIBILITY`
- `HIGH_CONGESTION`
- `BLE_PROXIMITY_DETECTED`
- `SENSOR_DISAGREEMENT`

These reason codes are the foundation for Gemini’s explanations.

---

## Operator Questions (Supported)

The Control Center UI supports three core operator questions:

1. **Why did robot X stop / slow / reroute?**  
2. **What’s happening in Zone C?**  
3. **Is this an isolated event, or part of a pattern?**

Gemini answers these by:
- retrieving recent decisions and telemetry
- summarizing trends and deltas
- citing specific contributing signals

Responses include:
- a natural-language explanation
- bullet-point evidence
- confidence level
- optional recommended operator action

---

## Reproducibility

### Local Development

```bash
cp .env.example .env
# Edit .env: uncomment KAFKA_BROKERS=broker:29092 for local Kafka
docker compose up --build
```

Access points:
- Control Center UI: http://localhost:3000
- Backend API: http://localhost:8080
- Simulator API: http://localhost:8000
- Kafka Control Center: http://localhost:9021

### Cloud Run Deployment

Prerequisites:
- [gcloud CLI](https://cloud.google.com/sdk/docs/install) installed and authenticated
- A GCP project with billing enabled
- A Confluent Cloud cluster with API credentials

```bash
# 1. Configure environment
cp .env.example .env
# Edit .env with your values:
#   - GOOGLE_CLOUD_PROJECT=your-project-id
#   - KAFKA_BROKERS=pkc-xxxxx.confluent.cloud:9092
#   - KAFKA_API_KEY / KAFKA_API_SECRET

# 2. Authenticate with GCP
gcloud auth login

# 3. One-time setup (enables APIs, creates Artifact Registry)
./deploy/setup-gcp.sh

# 4. Deploy all services
./deploy/cloud-run.sh

# 5. Teardown when done (deletes Cloud Run services)
./deploy/teardown.sh
```

The deployment script:
1. Builds all container images with Cloud Build
2. Deploys simulator, stream-processor, backend, and frontend to Cloud Run
3. Automatically wires up service URLs (backend URL injected into frontend at build time)
