# CoSense Cloud — Execution Work Plan

This document defines a **practical, time-boxed work plan** to complete the CoSense Cloud project for the Google AI Partner Catalyst challenge.

**Challenge Selected: Confluent**
> "Unleash the power of AI on data in motion! Build a next-generation AI application using Confluent and Google Cloud. Apply advanced AI/ML models to any real-time data stream to generate predictions, create dynamic experiences, or solve a compelling problem in a novel way."

This plan assumes:
- limited time (day job)
- Docker-first development
- correctness and clarity over polish
- intentional scope cuts where needed

---

## Definition of Done (DO NOT EXPAND)

The project is considered **done** when:

- `docker compose up --build` launches the full system
- Control Center UI shows robots and humans moving in Zone C
- Robots emit **SLOW / STOP / REROUTE** decisions with reason codes
- **Gemini monitors streaming data and proactively alerts** (agentic AI pattern)
- Operator can ask any question; Gemini answers with grounded evidence
- **Pipeline runs on Confluent Cloud** (not just local Docker)
- **Decisions stream to BigQuery** for real-time analytics
- Repo is clean, documented, and reproducible
- A 3-minute demo video emphasizes "AI on data in motion"

Anything beyond this is optional.

---

## Phase 0 — Lock the Contract ✅ DONE

**Goal:** prevent thrash.

### Tasks
- [x] Freeze event vocabulary:
  - actions: `SLOW`, `STOP`, `REROUTE`, `CONTINUE`
  - reason codes: `CLOSE_PROXIMITY`, `HIGH_RELATIVE_SPEED`, `LOW_VISIBILITY`, `HIGH_CONGESTION`, `BLE_PROXIMITY_DETECTED`, `SENSOR_DISAGREEMENT`
- [x] Freeze operator questions (exact wording)
- [x] Freeze supported scenario toggles:
  - visibility: normal/degraded/poor
  - connectivity: normal/degraded/offline

### Deliverables
- [x] `schemas/` package with Pydantic models
- [x] CLAUDE.md with key concepts

---

## Phase 1 — Headless Simulator ✅ DONE

**Goal:** deterministic telemetry source.

### Scope
- 1 zone (Zone C) with realistic warehouse layout
- Scalable robots/humans via `/scenario/reset` with params
- A* pathfinding between waypoints

### As-Built Features
- [x] Warehouse map from JSON (`maps/zone-c.json`)
- [x] A* pathfinding with obstacle avoidance
- [x] Robots navigate to waypoints, pause 1-10s at destination
- [x] Synthetic sensors: ultrasonic distance, BLE RSSI
- [x] Telemetry: `robot.telemetry`, `human.telemetry`, `zone.context`
- [x] Scenario control: start/stop/reset/toggle/scale
- [x] Individual robot control: `/robots/{id}/stop`, `/robots/{id}/start`
- [x] Manual override: stopped robots stay stopped until released
- [x] Accepts decisions from stream-processor via `/decision`

### Deliverables
- [x] `simulator/` - FastAPI + Dockerfile
- [x] `maps/zone-c.json` - Warehouse layout with zones, racks, waypoints
- [x] Supports Confluent Cloud via env vars

---

## Phase 2 — Streaming Fusion & Decisions ✅ DONE

**Goal:** real-time coordination logic.

### As-Built Features
- [x] Consume simulator topics via QuixStreams
- [x] State tracking for robot/human/zone
- [x] Risk scoring with 6 weighted factors:
  - Proximity (0.35), Relative velocity (0.25), Visibility (0.15)
  - BLE signal (0.10), Congestion (0.10), Sensor disagreement (0.05)
- [x] Action thresholds: STOP≥0.8, SLOW≥0.5, REROUTE≥0.3+congestion
- [x] Emit `coordination.decisions` with reason codes
- [x] **Apply decisions to simulator** via HTTP POST (robots actually stop/slow)
- [x] Skip robots with manual_override (user-stopped robots stay stopped)

### Deliverables
- [x] `stream-processor/` - QuixStreams + httpx + Dockerfile
- [x] Risk scoring logic in `src/risk.py`

---

## Phase 3 — Control Center UI ✅ DONE

**Goal:** operator-grade situational awareness + Gemini copilot integration.

### As-Built Features
- [x] Warehouse map rendering (zones, racks, conveyors, workstations, docks)
- [x] Real-time position updates (4Hz polling)
- [x] Robots color-coded by action: green=CONTINUE, yellow=SLOW, red=STOP, purple=REROUTE
- [x] Click robot on map → Entity Drawer with live details
- [x] Destination marker (pulsing target) for selected robot
- [x] Manual stop/start with "(Manual)" indicator
- [x] Reset dialog with parameters (robots, humans, visibility, connectivity)
- [x] Collapsible ROBOTS grid with color-coded state icons
- [x] Collapsible Recent Decisions (stops polling when collapsed)
- [x] Zone stats panel (robot/human count, congestion, visibility, connectivity)
- [x] Scenario toggles (visibility, connectivity dropdowns)
- [x] Bottom drawer: Ask Gemini panel with verbose mode
- [x] Dark theme CSS styling

### Deliverables
- [x] `control-center-webapp/` - React + TypeScript + Vite + Dockerfile
- [x] Running on `localhost:3000`

---

## Phase 4 — Gemini Operator Copilot ✅ DONE

**Goal:** agentic explainability with tool calling.

### Completed Tasks
- [x] Migrate to `google-genai` SDK
- [x] Implement 11 tool functions (6 query + 3 simulation + 2 robot control)
- [x] Automatic function calling via SDK
- [x] Q&A panel in UI with verbose mode
- [x] SSE streaming responses (real-time text display)
- [x] Markdown rendering for formatted output
- [x] Conversation history for follow-up questions
- [x] Resizable Ask Gemini panel with drag handle
- [x] Loading indicator with tool call progress

### Deliverables
- [x] `backend/src/gemini.py` - Automatic function calling + streaming
- [x] `backend/src/tools.py` - 11 tool functions
- [x] Working end-to-end: question → tools → streaming answer

---

## Phase 5 — Confluent Cloud Deployment ⬆️ PRIORITY

**Goal:** demonstrate real Confluent integration (not just local Docker).

**Key Benefit:** Confluent Cloud has built-in metrics UI showing topic throughput, consumer lag, and partition health — no need to build a custom metrics dashboard. Just screenshot the Console for the demo.

### Tasks
- [x] Add SASL_SSL auth support to all services (simulator, stream-processor, backend)
- [x] Add Kafka UI link in webapp header (configurable via VITE_CONFLUENT_URL)
- [x] Document env vars in `.env.example`
- [ ] Create Confluent Cloud cluster (free trial)
- [ ] Create topics: `robot.telemetry`, `human.telemetry`, `zone.context`, `coordination.decisions`
- [ ] Test full pipeline on Confluent Cloud
- [ ] Capture Confluent Console screenshots (topics, throughput, metrics)
- [ ] Document Confluent Cloud setup in README

### Environment Variables
```bash
KAFKA_BROKERS=<cluster>.confluent.cloud:9092
KAFKA_API_KEY=<key>
KAFKA_API_SECRET=<secret>
KAFKA_SECURITY_PROTOCOL=SASL_SSL
KAFKA_SASL_MECHANISM=PLAIN
```

### Deliverables
- [x] Code support for Confluent Cloud auth in all services
- [ ] Working pipeline on Confluent Cloud
- [ ] Screenshots of Confluent Console showing topics/throughput
- [ ] README section on Confluent Cloud setup

### Confluent Cloud Setup Steps
1. Create Confluent Cloud account at https://confluent.cloud (free trial available)
2. Create a Basic cluster in GCP (us-central1 recommended for Vertex AI proximity)
3. Create API key for the cluster (Cluster → API keys → Create key)
4. Create topics manually or let auto-create handle them:
   - `robot.telemetry`
   - `human.telemetry`
   - `zone.context`
   - `coordination.decisions`
   - `anomaly.alerts` (for Flink)
   - `anomaly.alerts.enriched` (for Flink)
5. Update `.env` with cluster credentials
6. For Flink: Enable Flink SQL in environment settings

---

## Phase 6 — AI on Streaming Data ⭐ KEY DIFFERENTIATOR

**Goal:** strengthen the "AI on data in motion" story for Confluent challenge.

### 6A. Streaming Topology Visualization

Make the data flow **visible** to judges.

```
┌─────────────────────────────────────────────────────────────────────┐
│                       STREAMING TOPOLOGY                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────┐                                                    │
│  │  Simulator   │                                                    │
│  └──────┬───────┘                                                    │
│         │                                                            │
│         ▼                                                            │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                    CONFLUENT CLOUD                              │ │
│  │  ┌────────────────┐ ┌────────────────┐ ┌────────────────┐      │ │
│  │  │robot.telemetry │ │human.telemetry │ │ zone.context   │      │ │
│  │  └───────┬────────┘ └───────┬────────┘ └───────┬────────┘      │ │
│  │          │                  │                   │                │ │
│  │          └────────┬─────────┴───────────────────┘                │ │
│  │                   ▼                                              │ │
│  │          ┌────────────────┐                                      │ │
│  │          │Stream Processor│                                      │ │
│  │          │ (Risk Scoring) │                                      │ │
│  │          └───────┬────────┘                                      │ │
│  │                  │                                               │ │
│  │                  ▼                                               │ │
│  │          ┌────────────────┐                                      │ │
│  │          │ coordination.  │                                      │ │
│  │          │  decisions     │                                      │ │
│  │          └───────┬────────┘                                      │ │
│  │                  │                                               │ │
│  │      ┌───────────┼───────────────────────────┐                   │ │
│  │      │           │                           │                   │ │
│  │      ▼           ▼                           ▼                   │ │
│  │  ┌────────┐ ┌────────────────────────────────────┐               │ │
│  │  │Backend │ │         FLINK SQL (AI)             │               │ │
│  │  │ + UI   │ │  ┌─────────────────────────────┐   │               │ │
│  │  └────────┘ │  │ ML_DETECT_ANOMALIES (ARIMA) │   │               │ │
│  │             │  └──────────────┬──────────────┘   │               │ │
│  │             │                 │                   │               │ │
│  │             │                 ▼                   │  ┌──────────┐│ │
│  │             │  ┌─────────────────────────────┐   │  │ Vertex   ││ │
│  │             │  │ ML_PREDICT (Gemini explain) │◄──┼──│ AI/      ││ │
│  │             │  └──────────────┬──────────────┘   │  │ Gemini   ││ │
│  │             │                 │                   │  └──────────┘│ │
│  │             └─────────────────┼───────────────────┘              │ │
│  │                               ▼                                  │ │
│  │                    ┌────────────────────┐                        │ │
│  │                    │ anomaly.alerts.    │                        │ │
│  │                    │ enriched           │──────► UI Alerts Panel │ │
│  │                    └────────────────────┘                        │ │
│  └──────────────────────────────────────────────────────────────────┘ │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Tasks
- [ ] Add topology diagram to README
- [ ] Embed simplified version in Control Center UI header/footer
- [ ] Capture Confluent Cloud Console topology screenshot

### 6B. UI Data Flow Emphasis

Make streaming **feel** real-time in the UI.

| Enhancement | Implementation | Demo Impact |
|-------------|----------------|-------------|
| Decision flash | Animate new decisions (pulse/glow) | "Watch decisions arrive" |
| Color-coded actions | STOP=red, SLOW=amber, REROUTE=purple, CONTINUE=green | Instant visual parsing |
| Decision count badge | Live counter incrementing | Shows throughput |
| Optional: flow lines | Animated lines from robot to decision log | Visual data flow |

### Tasks
- [ ] Add CSS animation for new decisions (fade-in + pulse)
- [x] Color-code decision badges by action type
- [x] Color-code robot icons in grid
- [x] Robot color legend in metrics panel
- [x] Robot hover highlighting (hover tile → glow on map)
- [ ] Add "Decisions/sec" counter in metrics panel
- [ ] Optional: animated connection lines on map

### 6C. Streaming Metrics Dashboard

Real-time health panel showing Confluent pipeline performance.

**Note:** Confluent Cloud Console already shows topic throughput, consumer lag, and partition metrics. May be sufficient for demo — custom dashboard is optional.

| Metric | Source | Display |
|--------|--------|---------|
| Decisions/second | Backend buffer | Live counter |
| Avg decision latency | timestamp diff | Gauge (ms) |
| Kafka consumer lag | Confluent Cloud Console | Screenshot |
| Topic throughput | Confluent Cloud Console | Screenshot |
| Active robots | Simulator state | Count |

### Tasks
- [ ] Add `/metrics` endpoint to backend (optional)
- [ ] Create collapsible "Stream Health" panel in UI (optional)
- [x] Use Confluent Cloud Console for throughput/lag metrics

### 6D. Flink AI Pipeline ⭐ HIGH IMPACT (Confluent Native)

**Goal:** Use Confluent Cloud's built-in AI features for anomaly detection + Gemini enrichment.

This approach uses **Confluent Flink SQL** instead of custom Python, demonstrating deep platform integration.

```
coordination.decisions → Flink SQL (ML_DETECT_ANOMALIES) → anomaly.alerts
                                    ↓
                         ML_PREDICT(Gemini via Vertex AI)
                                    ↓
                         anomaly.alerts.enriched → UI
```

**Demo line:** "Flink detected the anomaly using ARIMA. Gemini explained it. All in the stream."

#### Anomaly Types Detected

| Alert Type | Trigger | Flink Function |
|------------|---------|----------------|
| `DECISION_RATE_SPIKE` | Decision count exceeds ARIMA bounds | `ML_DETECT_ANOMALIES` |
| `REPEATED_ROBOT_STOP` | Same robot stops 2+ times in 30s | Windowed aggregation |
| `SENSOR_DISAGREEMENT_SPIKE` | 2+ sensor disagreements in 10s | Windowed aggregation |

#### Flink SQL Files

| File | Purpose |
|------|---------|
| `flink-sql/01-source-tables.sql` | Kafka source table definitions |
| `flink-sql/02-anomaly-detection.sql` | ML_DETECT_ANOMALIES pipeline |
| `flink-sql/03-gemini-enrichment.sql` | ML_PREDICT for AI explanations |

### Tasks
- [x] Create Flink SQL source tables for Kafka topics
- [x] Create anomaly detection pipeline with ML_DETECT_ANOMALIES
- [x] Create Gemini enrichment pipeline with ML_PREDICT
- [x] Document setup in `docs/flink-ai-pipeline.md`
- [ ] Create Confluent Cloud Flink environment (requires Confluent Cloud cluster first)
- [ ] Replace placeholders in SQL files (`${KAFKA_BROKERS}`, `${GCP_REGION}`, `${GCP_PROJECT_ID}`, `${GCP_SERVICE_ACCOUNT_KEY_JSON}`)
- [ ] Deploy SQL statements to Flink via Confluent Cloud Console
- [ ] Create `anomaly.alerts` and `anomaly.alerts.enriched` topics
- [ ] Test anomaly detection end-to-end
- [ ] Add backend endpoint to consume `anomaly.alerts.enriched`
- [ ] Add "AI Alerts" panel to UI

**Note:** The Flink SQL uses Confluent Cloud's managed ML functions (`ML_DETECT_ANOMALIES`, `ML_PREDICT`). These require Confluent Cloud Flink (not open-source Flink). The `ML_PREDICT` connection to Vertex AI requires a GCP service account with `aiplatform.endpoints.predict` permission.

### 6E. Congestion Scenario Demo

Pre-built "stress test" for demo impact.

**Demo script:**
> "Watch what happens when I flip this toggle to stress Zone C—decision rate spikes and Gemini responds live."

### Tasks
- [ ] Add "Stress Test" button (sets visibility=poor, adds 10 humans)
- [ ] Ensure Gemini proactively alerts on spike
- [ ] Document in README as demo highlight

### 6F. BigQuery Sink (If Time Permits)

Stream decisions to BigQuery for real-time analytics.

### Tasks
- [ ] Set up Confluent BigQuery Sink V2 connector
- [ ] Create BigQuery dataset: `cosense.decisions`
- [ ] Create BigQuery continuous query for pattern detection
- [ ] Show BigQuery dashboard in demo

### Deliverables
- [ ] Topology diagram in README and UI
- [ ] Animated decision visualization
- [ ] Streaming metrics panel
- [ ] Proactive Gemini alerts working
- [ ] Demo shows "AI reacting to data in motion"

---

## Phase 7 — Reproducibility & Cleanup ⏳ TODO

**Goal:** judge-proof repo.

### Tasks
- [x] `docker compose up` works from clean clone
- [x] `.env.example` complete
- [x] Docker hot-reload dev mode (`docker-compose.override.yml`)
- [ ] README quickstart verified
- [ ] Add OSI license file (MIT or Apache-2.0)
- [ ] Remove dead code and TODOs

### Deployment Requirements
- [x] Runnable locally via Docker Compose
- [x] Each service in a separate container (Cloud Run-ready)
- [x] Same containers deployable to Google Cloud Run with no code changes
- [x] Environment-based configuration (3 Confluent modes supported)

---

## Phase 8 — Demo & Submission ⏳ TODO

**Goal:** win the Confluent challenge.

### Demo Script (3 minutes)

| Time | Section | Key Points |
|------|---------|------------|
| 0:00-0:25 | Problem | Warehouse safety, operators need understanding not dashboards |
| 0:25-0:45 | Architecture | Show topology diagram: Confluent streaming → AI |
| 0:45-1:15 | Live Demo | Robots moving, **watch decisions flash in**, color-coded |
| 1:15-1:45 | Stress Test | **"Flip this toggle—watch decision rate spike"** + metrics panel |
| 1:45-2:20 | Gemini | Proactive alert fires: "I didn't ask, it noticed the spike" |
| 2:20-2:45 | Tech | Confluent Cloud Console, streaming metrics, real-time AI |
| 2:45-3:00 | Close | "AI on data in motion—not batch analytics with a streaming wrapper" |

### Key Demo Moments

1. **Decision Flash** — New decisions animate in with color (STOP=red pulse)
2. **Stress Test** — Toggle visibility=poor, add humans → decision rate visibly spikes
3. **Proactive Alert** — Gemini notices pattern without being asked
4. **Metrics Panel** — Show decisions/sec, latency, throughput in real-time

### Required Screenshots
- [ ] Control Center UI with robots moving
- [ ] Gemini Q&A with grounded answer
- [ ] **Confluent Cloud Console** showing topics and throughput
- [ ] BigQuery with streaming decisions (if implemented)

### Submission Checklist
- [ ] Hosted URL (Cloud Run)
- [ ] Public GitHub repo with OSI license
- [ ] README with deployment instructions
- [ ] 3-minute YouTube video
- [ ] Devpost form completed

---

## Service Naming

| Directory | Purpose |
|-----------|---------|
| `simulator/` | Headless world engine, telemetry generation |
| `stream-processor/` | Kafka stream processing, risk scoring |
| `backend/` | HTTP API, Gemini copilot, tool execution |
| `control-center-webapp/` | React operator UI |
| `schemas/` | Shared Pydantic models |
| `docs/` | Documentation |

## Documentation

- **[docs/kafka-topics.md](docs/kafka-topics.md)** — Kafka topics, message schemas, data flow diagram
- **[docs/flink-ai-pipeline.md](docs/flink-ai-pipeline.md)** — Flink SQL anomaly detection + Gemini enrichment

---

## Current Status Summary

| Phase | Status | Notes |
|-------|--------|-------|
| 0. Lock Contract | ✅ Done | Schemas defined |
| 1. Simulator | ✅ Done | A* pathfinding, waypoints, destination pause, manual override |
| 2. Stream Processor | ✅ Done | Risk scoring, decisions applied to simulator |
| 3. Control Center UI | ✅ Done | Full UI, color-coded robots, collapsible panels |
| 4. Gemini Copilot | ✅ Done | 11 tools, streaming, markdown, conversation history |
| 5. Confluent Cloud | 🔄 Partial | Code support done, cluster setup + testing pending |
| 6A. Topology Diagram | ⏳ TODO | README + UI |
| 6B. UI Data Flow | 🔄 Partial | Colors + legend + hover done, need decision animations |
| 6C. Metrics Dashboard | ⏳ TODO | Streaming health panel (optional - use Confluent Console) |
| 6D. Flink AI Pipeline | 🔄 Partial | SQL files + docs done, needs Confluent Cloud + deployment + UI |
| 6E. Congestion Demo | ⏳ TODO | Stress test button |
| 6F. BigQuery Sink | ⏳ TODO | If time permits |
| 7. Cleanup | 🔄 Partial | Docker + dev mode done, needs README + license |
| 8. Demo | ⏳ TODO | |

**Remaining Priority Order:**
1. **Confluent Cloud Cluster** - Create cluster, topics, test pipeline (BLOCKER for Flink)
2. **Flink AI Pipeline** - Deploy ML_DETECT_ANOMALIES + ML_PREDICT (key differentiator)
3. **UI Alerts Panel** - Show Flink-detected anomalies with Gemini explanations
4. **UI Data Flow** - Decision animations (quick win, high visual impact)
5. **Congestion Demo** - Stress test for wow factor
6. **README + License** - Judge requirements
7. **Demo video** - 3-minute walkthrough

---

## What Was Cut

| Item | Reason |
|------|--------|
| ~~Datadog~~ | Wrong challenge (Confluent selected) |
| ~~ElevenLabs~~ | Wrong challenge (Confluent selected) |

---

## Guiding Principle

> "Demonstrate how real-time data unlocks real-world challenges with AI."
> — Confluent Challenge Description

Build for **streaming-first AI**, not batch analytics with a streaming wrapper.

That wins the Confluent challenge.
