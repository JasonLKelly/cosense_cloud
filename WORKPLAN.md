# CoSense Cloud — Execution Work Plan

This document defines a **practical, time-boxed work plan** to complete the CoSense Cloud project for the Google AI Partner Catalyst challenge.

The goal is to deliver a **working, reproducible, end-to-end demo** by the submission deadline, with clear sponsor alignment and a strong demo narrative.

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
- Operator can ask:
  1. "Why did robot X stop / slow / reroute?"
  2. "What's happening in Zone C?"
  3. "Is this an isolated event, or part of a pattern?"
- Gemini answers are grounded, structured, and non-hallucinatory
- Datadog shows **decision-quality metrics**, not just infra health
- Repo is clean, documented, and reproducible
- A 2–3 minute demo video can be recorded without live debugging

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

## Phase 3 — Control Center UI ✅ DONE (Basic)

**Goal:** operator-grade situational awareness.

### UI Features Implemented
- [x] 2D map with robots (colored by action) and humans
- [x] Real-time position updates (polling)
- [x] Recent decisions panel
- [x] Start/Stop/Reset buttons
- [x] Zone status display

### Still TODO
- [ ] Add scenario toggle buttons (visibility, connectivity)
- [ ] Add Q&A panel for Gemini copilot
- [ ] Robot trails
- [ ] Better styling

### Deliverables
- [x] `control-center-webapp/` - React + TypeScript + Vite + Dockerfile
- [x] Running on `localhost:3000`

---

## Phase 4 — Gemini Operator Copilot 🔄 IN PROGRESS

**Goal:** agentic explainability with tool calling.

### Architecture

```
┌──────────────────────────────────────────────────────────┐
│               control-center-webapp                       │
│   [Ask anything...                              ] ▶       │
│   [verbose: ✓] → get_robot_state(robot-1) ✓               │
│                → get_nearby_entities(robot-1) ✓           │
│   Answer: Robot-1 stopped because...                      │
└──────────────────────────────────────────────────────────┘
                            │
                    POST /ask {question}
                            ▼
┌──────────────────────────────────────────────────────────┐
│                        backend                            │
│                                                           │
│   google-genai SDK + Automatic Function Calling           │
│   ┌────────────────────────────────────────────────────┐  │
│   │ response = client.models.generate_content(         │  │
│   │     model='gemini-2.0-flash',                      │  │
│   │     contents=question,                             │  │
│   │     config=GenerateContentConfig(                  │  │
│   │         system_instruction=SYSTEM_PROMPT,          │  │
│   │         tools=[get_robot_state, get_nearby_entities│  │
│   │                get_decisions, get_zone_context,    │  │
│   │                get_scenario_status, analyze_patterns│ │
│   │     )                                              │  │
│   │ )                                                  │  │
│   │ # SDK handles entire agent loop automatically      │  │
│   └────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

### Tool Definitions (Medium Granularity)

Nine Python functions passed directly to Gemini. SDK auto-generates schemas from docstrings + type hints.

**Query Tools:**
| Tool | Purpose | Source |
|------|---------|--------|
| `get_robot_state(robot_id, window_sec)` | Position, velocity, sensors, trajectory | Kafka |
| `get_nearby_entities(robot_id, radius_m)` | Humans/robots near a robot | Kafka |
| `get_decisions(robot_id?, zone_id?, limit)` | Recent coordination decisions | Kafka |
| `get_zone_context(zone_id)` | Visibility, congestion, counts | Kafka/Simulator |
| `get_scenario_status()` | Simulation state, toggles | Simulator REST |
| `analyze_patterns(window_sec, group_by)` | Aggregated stats for patterns | Kafka |

**Control Tools:**
| Tool | Purpose | Source |
|------|---------|--------|
| `start_simulation()` | Start the robot simulation | Simulator REST |
| `stop_simulation()` | Stop/pause the simulation | Simulator REST |
| `reset_simulation()` | Reset to initial state | Simulator REST |

### SDK Migration

| Old (deprecated) | New (google-genai) |
|------------------|-------------------|
| `google-generativeai` | `google-genai` |
| `import google.generativeai as genai` | `from google import genai` |
| `genai.configure(api_key=...)` | `genai.Client(vertexai=True, project=..., location=...)` |
| Manual agent loop | SDK automatic function calling |
| `FunctionDeclaration` schemas | Plain Python functions with docstrings |

### Tasks
- [x] Rename `api-gateway/` → `backend/`
- [x] Rename `control-center/` → `control-center-webapp/`
- [x] Migrate to `google-genai` SDK
- [ ] Implement KafkaHistoryReader for tool queries (using in-memory buffer for now)
- [x] Implement 9 tool functions (6 query + 3 control)
- [x] Update `/ask` endpoint to use automatic function calling
- [ ] Add Q&A panel to webapp (text input, answer display)
- [ ] Add verbose mode toggle (show tool calls)
- [ ] Test with Vertex AI auth (not API key)

### Constraints
- Gemini decides which tools to call (no frontend question-type detection)
- Gemini never makes decisions or invents facts
- All answers must cite evidence from tool results
- System instructions enforce grounding

### Deliverables
- [ ] `backend/src/gemini.py` - Simplified with automatic function calling
- [ ] `backend/src/tools.py` - 6 tool functions
- [ ] `backend/src/kafka_reader.py` - Kafka history queries
- [ ] `control-center-webapp/` - Q&A panel component
- [ ] Working end-to-end: question → tools → answer

---

## Phase 5 — Datadog Observability ⏳ TODO

**Goal:** prove this is a real system.

### Metrics (MUST HAVE)
- decision latency (end-to-end)
- action distribution
- near-miss rate
- uncertainty / conflict rate

### Tasks
- [ ] Instrument simulator, stream-processor, backend
- [ ] Create Datadog dashboard:
  - "Decision Quality"
  - "Pipeline Health"
- [ ] Add screenshots to `/docs`

### Deliverables
- observability working with keys
- graceful no-key fallback

---

## Phase 6 — ElevenLabs ⏳ TODO (CUT IF BEHIND)

**Goal:** polish, not complexity.

### Tasks
- [ ] Speak alert on STOP
- [ ] Speak Gemini summary (short)
- [ ] UI toggle for voice on/off

### Deliverables
- voice demo clip
- fallback to text-only

---

## Phase 7 — Reproducibility & Cleanup ⏳ TODO

**Goal:** judge-proof repo.

### Tasks
- [x] `docker compose up` works from clean clone
- [x] `.env.example` complete
- [ ] README quickstart verified
- [ ] Remove dead code and TODOs

### Deployment Requirements
- [x] Runnable locally via Docker Compose
- [x] Each service in a separate container (Cloud Run-ready)
- [x] Same containers deployable to Google Cloud Run with no code changes
- [x] Environment-based configuration (3 Confluent modes supported)

---

## Phase 8 — Demo & Submission ⏳ TODO

**Goal:** win.

### Tasks
- [ ] Record 2–3 min demo video
- [ ] Capture screenshots:
  - UI
  - Confluent Control Center
  - Datadog dashboard
- [ ] Final README pass
- [ ] Devpost submission

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
| 0. Lock Contract | ✅ Done | Schemas defined in `schemas/` |
| 1. Simulator | ✅ Done | Working, scalable |
| 2. Stream Processor | ✅ Done | QuixStreams, risk scoring |
| 3. Control Center UI | ✅ Basic | Needs Gemini panel, polish |
| 4. Gemini Copilot | 🔄 Partial | Needs SDK migration + tool calling |
| 5. Datadog | ⏳ TODO | |
| 6. ElevenLabs | ⏳ TODO | Cut if behind |
| 7. Cleanup | 🔄 Partial | Docker works, needs README |
| 8. Demo | ⏳ TODO | |

**Next Priority:** Phase 4 (Gemini) - migrate to google-genai SDK, implement tools, wire up UI

---

## Schedule Reality Check

**Minimum viable path:** ~7–9 focused days
**Comfortable path:** ~10–12 days
**Stretch polish:** only if ahead of schedule

If behind:
- cut ElevenLabs first
- then cut Datadog depth
- never cut Gemini explainability

---

## Guiding Principle

> A simple system that works end-to-end beats a sophisticated system that's half-built.

Build for **clarity, determinism, and explanation**.

That wins hackathons.
