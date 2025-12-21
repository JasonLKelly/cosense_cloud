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
- 1 zone (Zone C) - expandable
- 2+ robots (scalable via `/scenario/scale`)
- 2+ humans (scalable via `/scenario/scale`)
- simple kinematics (x, y, velocity, heading)

### Tasks
- [x] Simulator service emits:
  - `robot.telemetry`
  - `human.telemetry`
  - `zone.context`
- [x] Synthetic sensors:
  - ultrasonic distance
  - BLE RSSI (distance + noise)
- [x] Scenario control via REST:
  - `/scenario/start`, `/scenario/stop`, `/scenario/reset`
  - `/scenario/toggle` (visibility, connectivity)
  - `/scenario/scale` (add robots/humans)

### Deliverables
- [x] `simulator/` - FastAPI + Dockerfile
- [x] Supports Confluent Cloud via env vars

---

## Phase 2 — Streaming Fusion & Decisions ✅ DONE

**Goal:** real-time coordination logic.

### Tasks
- [x] Consume simulator topics via QuixStreams
- [x] State tracking for robot/human/zone
- [x] Compute:
  - risk score (weighted formula)
  - action mapping (CONTINUE/SLOW/STOP/REROUTE)
- [x] Emit:
  - `coordination.decisions` with reason codes

### Implementation
- QuixStreams for stream processing
- In-memory state store for windowed joins
- Risk scoring with 6 weighted factors

### Deliverables
- [x] `stream-processor/` - QuixStreams + Dockerfile
- [x] Risk scoring logic in `src/risk.py`

---

## Phase 3 — Control Center UI ✅ DONE

**Goal:** operator-grade situational awareness + Gemini copilot integration.

### Completed Tasks
- [x] Warehouse map with zones, racks, conveyors, workstations
- [x] Real-time position updates (4Hz polling)
- [x] Start/Stop/Reset buttons
- [x] Click robot → Entity Drawer with details
- [x] Bottom drawer: Ask Gemini panel
- [x] Right drawer: Zone stats, scenario toggles, decisions
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

### Deliverables
- [x] `backend/src/gemini.py` - Automatic function calling
- [x] `backend/src/tools.py` - 11 tool functions
- [x] Working end-to-end: question → tools → answer

---

## Phase 5 — Confluent Cloud Deployment ⬆️ PRIORITY

**Goal:** demonstrate real Confluent integration (not just local Docker).

### Tasks
- [ ] Create Confluent Cloud cluster (free trial)
- [ ] Configure topics: `robot.telemetry`, `human.telemetry`, `zone.context`, `coordination.decisions`
- [ ] Test full pipeline on Confluent Cloud
- [ ] Capture Confluent Console screenshots for submission
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
- [ ] Working pipeline on Confluent Cloud
- [ ] Screenshots of Confluent Console showing topics/throughput
- [ ] README section on Confluent Cloud setup

---

## Phase 6 — AI on Streaming Data ⭐ KEY DIFFERENTIATOR

**Goal:** strengthen the "AI on data in motion" story for Confluent challenge.

### 6A. Proactive Gemini Agent (High Impact, Low Effort)

Transform Gemini from "answers questions" to "monitors stream and alerts proactively."

```python
# Gemini watches decision stream, alerts on patterns
async def stream_monitor():
    async for decision in kafka_stream("coordination.decisions"):
        if should_alert(decision):  # e.g., repeated STOP, sensor disagreement
            alert = await gemini.analyze(f"Investigate: {decision}")
            push_alert_to_ui(alert)
```

**Demo line:** "I didn't ask Gemini anything. It's watching the stream and just alerted me."

### Tasks
- [ ] Add `/stream/monitor` endpoint that watches decisions
- [ ] Implement alert conditions:
  - Same robot stops 2+ times in 30 seconds
  - SENSOR_DISAGREEMENT reason code
  - Visibility degraded + multiple SLOW commands
- [ ] Push proactive alerts to UI via SSE
- [ ] Add "Gemini Alerts" panel to UI

### 6B. BigQuery Sink (Medium Effort, High Demo Value)

Stream decisions to BigQuery for real-time analytics + historical patterns.

### Tasks
- [ ] Set up Confluent BigQuery Sink V2 connector
- [ ] Create BigQuery dataset: `cosense.decisions`
- [ ] Create BigQuery continuous query for pattern detection
- [ ] Show BigQuery dashboard in demo

### 6C. Optional: Flink AI Functions (Stretch)

If time permits, add Flink anomaly detection:
```sql
SELECT robot_id, ANOMALY_DETECT(risk_score) as is_anomaly
FROM coordination_state;
```

**Note:** Requires Confluent Cloud early access program.

### Deliverables
- [ ] Proactive Gemini alerts working
- [ ] BigQuery receiving streaming decisions
- [ ] Demo shows "AI reacting to data in motion"

---

## Phase 7 — Reproducibility & Cleanup ⏳ TODO

**Goal:** judge-proof repo.

### Tasks
- [x] `docker compose up` works from clean clone
- [x] `.env.example` complete
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
| 0:25-0:50 | Architecture | Confluent streaming + Gemini AI |
| 0:50-1:30 | Live Demo | Robots moving, decisions appearing, scenario toggles |
| 1:30-2:20 | Gemini | Q&A + **proactive alerts** ("I didn't ask, it noticed") |
| 2:20-2:45 | Tech | Confluent Cloud, BigQuery sink, real-time AI |
| 2:45-3:00 | Close | "AI on data in motion" |

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

---

## Current Status Summary

| Phase | Status | Notes |
|-------|--------|-------|
| 0. Lock Contract | ✅ Done | Schemas defined |
| 1. Simulator | ✅ Done | Working, scalable |
| 2. Stream Processor | ✅ Done | QuixStreams, risk scoring |
| 3. Control Center UI | ✅ Done | Full UI with Gemini panel |
| 4. Gemini Copilot | ✅ Done | 11 tools, auto function calling |
| 5. Confluent Cloud | ⏳ TODO | **PRIORITY** |
| 6. AI on Streaming | ⏳ TODO | Proactive alerts + BigQuery |
| 7. Cleanup | 🔄 Partial | Docker works, needs README |
| 8. Demo | ⏳ TODO | |

**Remaining Priority Order:**
1. **Confluent Cloud** - Must demonstrate real Confluent integration
2. **Proactive Gemini** - "AI on data in motion" differentiator
3. **BigQuery Sink** - Shows full Google Cloud integration
4. **README + License** - Judge requirements
5. **Demo video** - 3-minute walkthrough

---

## What Was Cut

| Item | Reason |
|------|--------|
| ~~Datadog~~ | Wrong challenge (Confluent selected) |
| ~~ElevenLabs~~ | Wrong challenge (Confluent selected) |
| ~~Flink ML~~ | Requires early access, not essential |

---

## Guiding Principle

> "Demonstrate how real-time data unlocks real-world challenges with AI."
> — Confluent Challenge Description

Build for **streaming-first AI**, not batch analytics with a streaming wrapper.

That wins the Confluent challenge.
