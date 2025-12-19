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
  1. “Why did robot X stop / slow / reroute?”
  2. “What’s happening in Zone C?”
  3. “Is this an isolated event, or part of a pattern?”
- Gemini answers are grounded, structured, and non-hallucinatory
- Datadog shows **decision-quality metrics**, not just infra health
- Repo is clean, documented, and reproducible
- A 2–3 minute demo video can be recorded without live debugging

Anything beyond this is optional.

---

## Phase 0 — Lock the Contract (½ day)

**Goal:** prevent thrash.

### Tasks
- [ ] Freeze event vocabulary:
  - actions: `SLOW`, `STOP`, `REROUTE`
  - reason codes (max 6)
- [ ] Freeze operator questions (exact wording)
- [ ] Freeze supported scenario toggles:
  - vision degraded
  - connectivity degraded

### Deliverables
- `docs/api.md` (schemas only, no code)
- checklist of non-goals

**STOP HERE until this is done.**

---

## Phase 1 — Headless Simulator (1–1.5 days)

**Goal:** deterministic telemetry source.

### Scope (minimal)
- 1 zone (Zone C)
- 2 robots
- 2 humans
- simple kinematics (x, y, velocity)

### Tasks
- [ ] Simulator service emits:
  - `robot.telemetry`
  - `human.telemetry`
  - `zone.context`
- [ ] Synthetic sensors:
  - ultrasonic distance
  - BLE RSSI (distance + noise)
- [ ] Scenario toggles via REST:
  - `/scenario/start`
  - `/scenario/toggle`

### Deliverables
- simulator container
- README explaining signals
- deterministic seed mode

**No UI. No Kafka logic here.**

---

## Phase 2 — Streaming Fusion & Decisions (1.5–2 days)

**Goal:** real-time coordination logic.

### Tasks
- [ ] Consume simulator topics via Confluent Platform
- [ ] Windowed join:
  - robot ↔ nearest human ↔ zone
- [ ] Compute:
  - risk score (simple formula)
  - action mapping
- [ ] Emit:
  - `coordination.state`
  - `coordination.decisions`

### Constraints
- All logic must be explainable
- No ML here — pure rules + thresholds
- Attach `reason_codes` to every decision

### Deliverables
- stream processor container
- unit tests for decision mapping
- schema registered in Schema Registry

---

## Phase 3 — Control Center UI (1–1.5 days)

**Goal:** operator-grade situational awareness.

### UI Features (ONLY THESE)
- 2D map (canvas or SVG)
- robots + humans + trails
- current action badge per robot
- incident timeline (decisions only)

### Tasks
- [ ] Subscribe to state + decision streams
- [ ] Render positions and actions
- [ ] Add scenario toggle buttons
- [ ] Add “Ask a question” panel (stubbed)

### Deliverables
- Control Center running on `localhost:3000`
- Screenshot-ready UI

**No styling rabbit holes. Functional > pretty.**

---

## Phase 4 — Gemini Operator Copilot (1 day)

**Goal:** explainability with guardrails.

### Tasks
- [ ] Define tool interface:
  - fetch recent decisions
  - fetch zone summary
- [ ] Define structured output schema:
  - answer
  - evidence
  - confidence
- [ ] Implement 3 fixed questions
- [ ] Refuse to answer if data missing

### Constraints
- Gemini never makes decisions
- Gemini never invents facts
- All answers cite telemetry

### Deliverables
- `llm/prompts/`
- `llm/schemas/`
- working Q&A in UI

---

## Phase 5 — Datadog Observability (½–1 day)

**Goal:** prove this is a real system.

### Metrics (MUST HAVE)
- decision latency (end-to-end)
- action distribution
- near-miss rate
- uncertainty / conflict rate

### Tasks
- [ ] Instrument simulator, processor, gateway
- [ ] Create Datadog dashboard:
  - “Decision Quality”
  - “Pipeline Health”
- [ ] Add screenshots to `/docs`

### Deliverables
- observability working with keys
- graceful no-key fallback

---

## Phase 6 — ElevenLabs (½ day)

**Goal:** polish, not complexity.

### Tasks
- [ ] Speak alert on STOP
- [ ] Speak Gemini summary (short)
- [ ] UI toggle for voice on/off

### Deliverables
- voice demo clip
- fallback to text-only

---

## Phase 7 — Reproducibility & Cleanup (½ day)

**Goal:** judge-proof repo.

### Tasks
- [ ] `docker compose up` works from clean clone
- [ ] `.env.example` complete
- [ ] README quickstart verified
- [ ] Remove dead code and TODOs

---

## Phase 8 — Demo & Submission (½ day)

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

> A simple system that works end-to-end beats a sophisticated system that’s half-built.

Build for **clarity, determinism, and explanation**.

That wins hackathons.
