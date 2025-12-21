# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Goals

1. **Win the Google AI Partner Catalyst hackathon** (deadline: Dec 31, 2025)
2. Make this demoable for other purposes afterward

## Hackathon Context

**Competition:** Google AI Partner Catalyst (ai-partner-catalyst.devpost.com)

**GCP Account:** urbanality@gmail.com

**Required Technologies:**
- Google Cloud (Vertex AI / Gemini) - mandatory
- Partner integration: Confluent (primary), Datadog, ElevenLabs

**Judging Criteria:**
1. Technological Implementation - quality integration of Google Cloud + partner services
2. Design - thoughtful UX
3. Potential Impact - real-world benefit
4. Quality of Idea - creativity and uniqueness

**Submission Requirements:**
- Hosted application URL
- Public repo with OSI license
- README with deployment instructions
- 3-minute video walkthrough
- Evidence: dashboards, detection rules, incident examples

**What Wins:** Deep integration of both platforms (not separate components), robust technical execution, real-world applicability, innovative approach.

## Project Overview

CoSense Cloud is a real-time human-robot coordination system for warehouse environments. It combines streaming telemetry (Confluent), rule-based decision logic, and LLM-based operator copilots (Gemini) for explainability.

## Build & Run Commands

```bash
# Start the full system
cp .env.example .env
docker compose up --build

# Access points after startup:
# - Control Center UI: http://localhost:3000
# - Backend API: http://localhost:8080
# - Simulator API: http://localhost:8000
# - Kafka Control Center: http://localhost:9021
# - Schema Registry: http://localhost:8081
```

## Tech Stack

- **Backend:** Python 3.12 + FastAPI + Pydantic
- **Streaming:** QuixStreams (stream-processor), confluent-kafka (others)
- **Frontend:** React + TypeScript (control-center-webapp)
- **LLM:** Google Gemini via `google-genai` SDK with automatic function calling
- **Infrastructure:** Docker Compose (local), Cloud Run (production)

## Confluent Deployment Modes

All services support three Kafka deployment modes via environment variables:

| Mode | KAFKA_BROKERS | Auth | Use Case |
|------|---------------|------|----------|
| **1. Local Docker** | `broker:29092` | None | Development |
| **2. Cloud Run self-host** | `<cloud-run-url>:9092` | None/optional | Self-managed prod |
| **3. Confluent Cloud** | `<cluster>.confluent.cloud:9092` | SASL_SSL | Hackathon submission |

For Confluent Cloud, set:
```
KAFKA_API_KEY=<key>
KAFKA_API_SECRET=<secret>
KAFKA_SECURITY_PROTOCOL=SASL_SSL
KAFKA_SASL_MECHANISM=PLAIN
```

## Architecture

The system consists of four main services communicating via Kafka:

1. **simulator/** - Headless World Engine that generates robot/human telemetry for Zone C. Emits `robot.telemetry`, `human.telemetry`, `zone.context` events. Provides REST endpoints for scenario control (`/scenario/start`, `/scenario/toggle`).

2. **stream-processor/** - Consumes telemetry via Confluent Platform, performs windowed joins (robot ↔ human ↔ zone), computes risk scores, and emits `coordination.state` and `coordination.decisions` with reason codes. Pure rules + thresholds, no ML.

3. **backend/** - HTTP API layer (port 8080) connecting the UI to Kafka and Gemini. Houses the Gemini operator copilot with tool-calling capabilities. Tools query Kafka history and simulator state.

4. **control-center-webapp/** - React UI (port 3000) showing 2D map with robots/humans, decision badges, and operator Q&A panel.

### Gemini Copilot Tools

The copilot uses 11 tools that Gemini calls automatically via the `google-genai` SDK:

**Query Tools:**
| Tool | Purpose |
|------|---------|
| `get_robot_state` | Robot position, velocity, sensors, trajectory |
| `get_nearby_entities` | Humans/robots near a specific robot |
| `get_decisions` | Recent coordination decisions with filters |
| `get_zone_context` | Zone visibility, congestion, entity counts |
| `get_scenario_status` | Simulation state and toggles |
| `analyze_patterns` | Aggregated stats for pattern detection |

**Simulation Control:**
| Tool | Purpose |
|------|---------|
| `start_simulation` | Start the robot simulation |
| `stop_simulation` | Stop/pause the simulation |
| `reset_simulation` | Reset simulation to initial state |

**Robot Control:**
| Tool | Purpose |
|------|---------|
| `stop_robot(robot_id)` | Stop a specific robot |
| `start_robot(robot_id)` | Resume a specific robot |

## Key Concepts

**Decision Actions:** `SLOW`, `STOP`, `REROUTE`

**Reason Codes:** `CLOSE_PROXIMITY`, `HIGH_RELATIVE_SPEED`, `LOW_VISIBILITY`, `HIGH_CONGESTION`, `BLE_PROXIMITY_DETECTED`, `SENSOR_DISAGREEMENT`

**Example Operator Questions:**
- "Why did robot-1 stop?"
- "What's happening in Zone C?"
- "Is this an isolated event, or part of a pattern?"
- Any free-form question — Gemini decides which tools to call

## Design Principles

- Gemini never makes decisions or invents facts; all answers must cite telemetry
- All coordination logic must be explainable with attached reason_codes
- Local Docker development mirrors Cloud Run deployment
- Prioritize correctness and clarity over polish
- A simple system that works end-to-end beats a sophisticated system that's half-built

## Git Commit Rules

- Do NOT add "Generated with Claude Code" footers
- Do NOT add "Co-Authored-By" lines
- Keep commit messages clean and conventional

## Hackathon Priority Order

If behind schedule, cut in this order:
1. ElevenLabs voice (cut first)
2. Datadog depth
3. Never cut Gemini explainability (core differentiator)
