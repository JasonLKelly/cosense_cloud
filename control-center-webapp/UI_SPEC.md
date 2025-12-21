# CoSense Control Center — UI Specification

## Overview

Single-page operator interface for real-time warehouse robot coordination.
Prioritizes situational awareness + Gemini-powered explainability.

---

## Layout Structure

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Header: CoSense Control Center          [Start] [Stop] [Reset]   Status │
├─────────────────────────────────────────────────────────────┬───────────┤
│                                                             │           │
│                                                             │  Right    │
│                    Full-Screen 2D Map                       │  Drawer   │
│                                                             │  (Metrics)│
│                    • Robots (colored by action)             │           │
│                    • Humans (blue dots)                     │           │
│                    • Zone boundaries                        │           │
│                                                             │           │
│                                                             │           │
├─────────────────────────────────────────────────────────────┴───────────┤
│  Bottom Drawer: Ask Gemini                                    [Toggle]  │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │ [Ask anything about the warehouse...]                         [▶] │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│  [Verbose ☐]  Tool calls: get_robot_state → get_decisions → ...        │
│  Answer: Robot-1 stopped because human H-2 was 1.2m away...            │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Components

### 1. Header Bar
- Title: "CoSense Control Center"
- Simulation controls: Start, Stop, Reset buttons
- Status indicator: 🟢 Running / ⚪ Stopped
- Sim time display

### 2. Map View (Main Canvas)

**Fixed Elements:**
- Zone boundary (Zone C outline)
- Grid or subtle coordinate reference

**Live Entities:**
| Entity | Visual | Color Logic |
|--------|--------|-------------|
| Robot | Circle with direction indicator | Green=CONTINUE, Yellow=SLOW, Red=STOP, Purple=REROUTE |
| Human | Smaller blue circle | Blue always |

**Interactions:**
- Hover: Show entity ID tooltip
- Click robot: Open Entity Drawer
- Click human: Show basic info

### 3. Right Drawer (Metrics Panel)

**Zone Summary:**
- Robot count
- Human count
- Visibility: normal/degraded/poor
- Connectivity: normal/degraded/offline
- Congestion: 0-100%

**Recent Decisions:**
- Last 5-10 decisions
- Format: `[robot_id]: ACTION - reason`
- Color-coded by action

**Scenario Toggles:**
- [ ] Degrade visibility
- [ ] Degrade connectivity

### 4. Entity Drawer (Opens on Robot Click)

**Robot Details:**
| Field | Example |
|-------|---------|
| Robot ID | robot-1 |
| Position | (12.5, 8.3) |
| Velocity | 1.2 m/s |
| Status | SLOW |
| Reason | CLOSE_PROXIMITY |

**Actions:**
- ⏹ Stop Robot
- ▶️ Start Robot

**Close:** X button or click outside

### 5. Bottom Drawer (Ask Gemini)

**Input:**
- Text input: "Ask anything about the warehouse..."
- Submit button

**Quick Actions (optional):**
- "Why did [selected robot] stop?"
- "What's happening in Zone C?"
- "Any patterns?"

**Response Display:**
- Confidence badge: HIGH/MEDIUM/LOW
- Answer text (markdown-ish)
- Tool calls list (if verbose mode enabled)

**Verbose Mode Toggle:**
- Shows which tools Gemini called
- Format: `→ get_robot_state(robot-1) ✓`

---

## V1 Build Plan

### Priority Order

1. **Map with live entities** (have basic version)
2. **Entity drawer on robot click** (stop/start buttons)
3. **Bottom drawer with Ask Gemini**
4. **Right drawer with metrics**
5. **Verbose mode toggle**

### Tech Stack
- React 18 + TypeScript
- Vite (already set up)
- Tailwind CSS (add)
- No component library needed for v1

### API Endpoints Used

| Endpoint | Purpose |
|----------|---------|
| `GET /simulator/state` | Robot/human positions, zone info |
| `GET /decisions` | Recent coordination decisions |
| `POST /ask` | Ask Gemini a question |
| `POST /robots/{id}/stop` | Stop specific robot |
| `POST /robots/{id}/start` | Start specific robot |
| `POST /scenario/start` | Start simulation |
| `POST /scenario/stop` | Stop simulation |
| `POST /scenario/reset` | Reset simulation |
| `POST /scenario/toggle` | Toggle visibility/connectivity |

### File Structure (Proposed)

```
control-center-webapp/
├── src/
│   ├── main.tsx
│   ├── App.tsx                 # Layout + routing
│   ├── components/
│   │   ├── Map.tsx             # 2D canvas with entities
│   │   ├── EntityDrawer.tsx    # Robot details + actions
│   │   ├── AskGemini.tsx       # Bottom drawer
│   │   ├── MetricsPanel.tsx    # Right drawer
│   │   └── Header.tsx          # Controls + status
│   ├── hooks/
│   │   ├── useSimState.ts      # Polling /simulator/state
│   │   ├── useDecisions.ts     # Polling /decisions
│   │   └── useGemini.ts        # POST /ask
│   └── types.ts                # TypeScript interfaces
```

---

## Alignment with Requirements

| Requirement | Status | Notes |
|-------------|--------|-------|
| Shows robots/humans moving | ✅ | Map view |
| Shows SLOW/STOP/REROUTE decisions | ✅ | Color-coded + decisions panel |
| Operator can ask "Why did robot X stop?" | ✅ | Ask Gemini drawer |
| Operator can ask "What's happening in Zone C?" | ✅ | Ask Gemini drawer |
| Operator can ask "Is this a pattern?" | ✅ | Ask Gemini drawer |
| Gemini answers are grounded | ✅ | Backend enforces via tools |
| Click robot → see info → stop | ✅ | Entity drawer |
| Verbose tool call display | ✅ | Toggle in Ask Gemini |
| Scenario toggles | ✅ | Right drawer |

---

## Cut from V1 (Nice-to-Have)

- Robot trails (ghost lines)
- Planned paths (destination polylines)
- Warehouse fixtures (racks, conveyors)
- System logs export
- Force reroute action
- Deterministic replay seeding
- ElevenLabs voice I/O (Phase 6)

---

## Design Tokens (V1)

```css
/* Colors */
--bg-primary: #1a1a2e;
--bg-secondary: #2a2a4a;
--text-primary: #ffffff;
--text-muted: #888888;

--robot-continue: #4ade80;  /* green */
--robot-slow: #facc15;      /* yellow */
--robot-stop: #f87171;      /* red */
--robot-reroute: #a78bfa;   /* purple */
--human: #60a5fa;           /* blue */

/* Spacing */
--drawer-width: 320px;
--header-height: 56px;
--bottom-drawer-height: 200px;
```
