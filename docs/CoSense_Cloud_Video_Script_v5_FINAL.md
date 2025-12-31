# CoSense Cloud — Video Script v5 (3:00)
## *Modular Script — Works Now, Upgradeable If Time Permits*

**Strategy:** Core script works without ML_PREDICT features. Optional sections marked for insertion if you complete Options 1 & 2.

---

## TITLE SCREEN (0:00–0:03)
*[SCREEN: Title card with logo]*

**CoSense Cloud**
*AI on Data in Motion*

**github.com/JasonLKelly/cosense_cloud**

---

## HOOK (0:03–0:15)
*[B-ROLL: Video 1 — AGV robots moving boxes, workers in background]*

**VOICEOVER:**
> "Eighty thousand warehouse injuries per year in the US — and climbing. Autonomous robots were supposed to help, but they created a new problem: humans and machines sharing space at speed."

**[TEXT ON SCREEN: "80,000+ warehouse injuries per year"]**

---

## THE PROBLEM → SOLUTION (0:15–0:30)
*[B-ROLL: Video 2 — Worker at screen, COMPOSITE CoSense UI onto green screen]*

**VOICEOVER:**
> "Operators are drowning in dashboards, reacting to alerts *after* something goes wrong. What if the streaming platform could detect anomalies the moment they emerge — and an AI copilot could help you understand them?"

---

## THE ARCHITECTURE (0:30–0:55)

### BASE VERSION (No ML_PREDICT)

*[SCREEN: Architecture diagram with animated data flow]*

**VOICEOVER:**
> "CoSense Cloud is real-time coordination built on Confluent Cloud and Google Cloud."

*[SCREEN: Highlight QuixStreams + Kafka Topics]*

> "Robots and humans stream telemetry at ten hertz into Kafka topics. A QuixStreams processor — Confluent's Python DSL — joins the data, calculates weighted risk scores, and emits coordination decisions. Fifty milliseconds, every cycle."

**[TEXT ON SCREEN: "QuixStreams • 10Hz • 50ms Decisions"]**

*[SCREEN: Highlight Flink + ML_DETECT_ANOMALIES]*

> "Confluent's managed Flink runs ML_DETECT_ANOMALIES — built-in ARIMA — directly in SQL. No external model server. The anomaly detection runs *inside the stream*, learning normal patterns and flagging outliers at stream speed."

**[TEXT ON SCREEN: "Flink SQL • ML_DETECT_ANOMALIES • ARIMA"]**

*[SCREEN: Highlight Gemini on side]*

> "When operators need deeper analysis, Gemini on Vertex AI is connected as an interactive copilot — querying live Kafka state through function calling."

**[TEXT ON SCREEN: "Streaming ML + AI Copilot"]**

---

### ⬆️ UPGRADED VERSION (If Options 1 & 2 Complete)

*Replace the Flink section above with:*

*[SCREEN: Highlight Flink + ML_DETECT_ANOMALIES + ML_PREDICT]*

> "Confluent's managed Flink does two things. First, ML_DETECT_ANOMALIES — built-in ARIMA — flags statistical outliers at stream speed. Then ML_PREDICT calls Vertex AI models directly from SQL: a classifier categorizes each anomaly, and every five minutes, Gemini generates a shift summary. All inside Flink. No external orchestration."

**[TEXT ON SCREEN: "ML_DETECT_ANOMALIES → ML_PREDICT → Vertex AI"]**

---

## LIVE DEMO — The Flow (0:55–1:25)
*[SCREEN: Control Center UI — robots moving on map]*

**VOICEOVER:**
> "Here's Zone C. Robots navigating, humans working. The decision stream shows every coordination event — color-coded, flowing from Confluent."

*[SCREEN: Decisions flashing in — STOP/SLOW/CONTINUE]*

> "Red means STOP. A robot got too close to a human. The system prevented a collision. Each decision flows through Kafka and arrives here in under a hundred milliseconds."

*[CLICK: Select a robot, show Entity Drawer]*

> "Click any robot — live telemetry, current action, reason codes. Operators see *why*, not just *what*."

---

## STRESS TEST (1:25–1:50)

### BASE VERSION (No Classification)

*[SCREEN: Click visibility dropdown, select "poor"]*

**VOICEOVER:**
> "Let's stress the system. Dropping visibility to poor..."

*[SCREEN: Open reset dialog, increase humans, click reset]*

> "...and adding more humans."

*[SCREEN: Decision rate spikes, alert appears]*

> "Watch the decision rate spike. Flink's ARIMA model sees the surge exceed confidence bounds and fires an alert. No API call. No external service. The ML ran inside Flink SQL."

**[TEXT ON SCREEN: "ML_DETECT_ANOMALIES • ARIMA • In-Stream"]**

---

### ⬆️ UPGRADED VERSION (If Option 2 Complete)

*Add after "fires an alert":*

> "And watch — ML_PREDICT classifies it instantly: ENVIRONMENTAL. The classifier runs on Vertex AI, called directly from Flink SQL. Low latency, deterministic categories."

**[TEXT ON SCREEN: "ML_PREDICT → Classification → ENVIRONMENTAL"]**

*[SCREEN: Alert shows category badge]*

---

## GEMINI — Interactive AI Copilot (1:50–2:20)
*[SCREEN: Ask Gemini panel — type a question]*

**VOICEOVER:**
> "Now the operator wants context. 'What's causing the spike in Zone C?'"

*[SCREEN: Streaming response with tool calls visible]*

> "Gemini uses function calling to query live Kafka state — eleven tools connected to decisions, telemetry, and zone context. The response streams back, grounded in actual data."

**[TEXT ON SCREEN: "11 Tools • Function Calling • Grounded in Kafka"]**

*[SCREEN: Gemini response completes]*

> "'Visibility dropped while human density increased. Recommend clearing the northwest quadrant.' Flink detects at speed. Gemini explains on demand."

---

### ⬆️ OPTIONAL INSERT (If Option 1 Complete) — Add at 2:15

*[SCREEN: Summary card appears in UI]*

> "And every five minutes, Flink calls Gemini via ML_PREDICT to generate a shift summary — batching all anomalies into one AI-written briefing. Not per-alert. Batched intelligence."

**[TEXT ON SCREEN: "ML_PREDICT → Gemini → Shift Summaries"]**

*[SCREEN: Show summary text]*

---

## TECH CREDIBILITY (2:20–2:45)

### BASE VERSION

*[SCREEN: Confluent Cloud Console — topics]*

**VOICEOVER:**
> "This runs on Confluent Cloud. Seven Kafka topics. Managed Flink running ML_DETECT_ANOMALIES."

**[TEXT ON SCREEN: "Confluent Cloud • Managed Flink"]**

*[SCREEN: Google Cloud Console — Vertex AI]*

> "Gemini on Vertex AI with function calling. Streaming ML plus conversational AI."

**[TEXT ON SCREEN: "Vertex AI • Gemini • 11 Tools"]**

---

### ⬆️ UPGRADED VERSION (If Options 1 & 2 Complete)

*Replace above with:*

*[SCREEN: Confluent Cloud Console — topics]*

**VOICEOVER:**
> "This runs on Confluent Cloud. Seven Kafka topics. Managed Flink running ML_DETECT_ANOMALIES *and* ML_PREDICT."

*[SCREEN: Flink SQL showing ML_PREDICT statement]*

> "Two Vertex AI connections from Flink SQL — a classifier for instant categorization, Gemini for periodic summaries. Plus interactive function calling for operators."

**[TEXT ON SCREEN: "ML_DETECT_ANOMALIES • ML_PREDICT • Function Calling"]**

*[SCREEN: Google Cloud Console — Vertex AI endpoints]*

> "Three AI touchpoints: streaming anomaly detection, streaming classification, and conversational copilot. All on Confluent plus Google Cloud."

---

## CLOSE (2:45–3:00)
*[B-ROLL: Video 1 or 2]*

### BASE VERSION

**VOICEOVER:**
> "CoSense Cloud pairs streaming ML with an AI copilot. Flink's ARIMA detects anomalies at stream speed. Gemini helps operators understand and act. The right ML for the right job. That's AI on data in motion."

**[TEXT ON SCREEN: "AI on data in motion."]**

> "Real-time detection. Intelligent assistance. Real impact."

---

### ⬆️ UPGRADED VERSION (If Options 1 & 2 Complete)

**VOICEOVER:**
> "CoSense Cloud runs AI at every layer. ML_DETECT_ANOMALIES for streaming detection. ML_PREDICT for classification and summaries. Gemini for interactive analysis. All connected through Confluent Cloud and Vertex AI. That's AI on data in motion."

**[TEXT ON SCREEN: "AI on data in motion."]**

> "Real-time detection. Real-time classification. Real impact."

---

*[SCREEN: End card with logos and GitHub URL]*

**[LOGOS: CoSense Cloud + Confluent + Google Cloud]**
**github.com/JasonLKelly/cosense_cloud**

---

# TIMING GUIDE

| Section | Base Duration | With Upgrades |
|---------|---------------|---------------|
| Title | 0:00–0:03 | Same |
| Hook | 0:03–0:15 | Same |
| Problem/Solution | 0:15–0:30 | Same |
| Architecture | 0:30–0:55 | Same (swap voiceover) |
| Live Demo | 0:55–1:25 | Same |
| Stress Test | 1:25–1:50 | +5s for classification callout |
| Gemini Q&A | 1:50–2:20 | +5s for summary insert |
| Tech Credibility | 2:20–2:45 | Same (swap voiceover) |
| Close | 2:45–3:00 | Same (swap voiceover) |

**If adding both upgrades:** Trim 5s from Gemini Q&A section (cut the second question) and 5s from Tech Credibility (tighten console shots).

---

# UPGRADE CHECKLIST

## Option 1: Periodic Summaries
- [ ] Create Gemini connection in Flink
- [ ] Create summarizer model
- [ ] Deploy 5-minute window summary SQL
- [ ] Add summary card to UI
- [ ] Record upgraded demo footage

## Option 2: Classification
- [ ] Train AutoML model (or mock with rules-based)
- [ ] Create classifier connection in Flink
- [ ] Deploy classification SQL
- [ ] Add category badges to alert UI
- [ ] Record upgraded demo footage

## If Both Complete:
- [ ] Swap architecture voiceover
- [ ] Add classification callout in stress test
- [ ] Add summary insert in Gemini section
- [ ] Swap tech credibility voiceover
- [ ] Swap close voiceover

---

# QUICK RECORDING PLAN

## Must Record (Base Version) — Do First
1. Live demo: robots moving, decisions flowing (30s)
2. Stress test: visibility dropdown → alert appears (25s)
3. Gemini Q&A: type question → response streams (30s)
4. Confluent Console: topics view (10s)
5. GCP Console: Vertex AI (10s)

## Record If Time (Upgrades)
6. Stress test v2: alert with category badge (10s)
7. Summary card appearing in UI (10s)
8. Flink SQL showing ML_PREDICT (10s)

---

# VOICEOVER SCRIPT (Plain Text for Recording)

## Base Version — Read This First

**[0:03]** "Eighty thousand warehouse injuries per year in the US — and climbing. Autonomous robots were supposed to help, but they created a new problem: humans and machines sharing space at speed."

**[0:15]** "Operators are drowning in dashboards, reacting to alerts after something goes wrong. What if the streaming platform could detect anomalies the moment they emerge — and an AI copilot could help you understand them?"

**[0:30]** "CoSense Cloud is real-time coordination built on Confluent Cloud and Google Cloud. Robots and humans stream telemetry at ten hertz into Kafka topics. A QuixStreams processor — Confluent's Python DSL — joins the data, calculates weighted risk scores, and emits coordination decisions. Fifty milliseconds, every cycle. Confluent's managed Flink runs ML_DETECT_ANOMALIES — built-in ARIMA — directly in SQL. No external model server. The anomaly detection runs inside the stream, learning normal patterns and flagging outliers at stream speed. When operators need deeper analysis, Gemini on Vertex AI is connected as an interactive copilot — querying live Kafka state through function calling."

**[0:55]** "Here's Zone C. Robots navigating, humans working. The decision stream shows every coordination event — color-coded, flowing from Confluent. Red means STOP. A robot got too close to a human. The system prevented a collision. Each decision flows through Kafka and arrives here in under a hundred milliseconds. Click any robot — live telemetry, current action, reason codes. Operators see why, not just what."

**[1:25]** "Let's stress the system. Dropping visibility to poor... and adding more humans. Watch the decision rate spike. Flink's ARIMA model sees the surge exceed confidence bounds and fires an alert. No API call. No external service. The ML ran inside Flink SQL."

**[1:50]** "Now the operator wants context. What's causing the spike in Zone C? Gemini uses function calling to query live Kafka state — eleven tools connected to decisions, telemetry, and zone context. The response streams back, grounded in actual data. Visibility dropped while human density increased. Recommend clearing the northwest quadrant. Flink detects at speed. Gemini explains on demand."

**[2:20]** "This runs on Confluent Cloud. Seven Kafka topics. Managed Flink running ML_DETECT_ANOMALIES. Gemini on Vertex AI with function calling. Streaming ML plus conversational AI."

**[2:45]** "CoSense Cloud pairs streaming ML with an AI copilot. Flink's ARIMA detects anomalies at stream speed. Gemini helps operators understand and act. The right ML for the right job. That's AI on data in motion. Real-time detection. Intelligent assistance. Real impact."

---

## Upgraded Sections — Record These If Time

**[0:30 Architecture — Replace]** "CoSense Cloud is real-time coordination built on Confluent Cloud and Google Cloud. Robots and humans stream telemetry at ten hertz into Kafka topics. A QuixStreams processor joins the data, calculates risk scores, and emits decisions. Fifty milliseconds, every cycle. Confluent's managed Flink does two things. First, ML_DETECT_ANOMALIES — built-in ARIMA — flags statistical outliers at stream speed. Then ML_PREDICT calls Vertex AI models directly from SQL: a classifier categorizes each anomaly, and every five minutes, Gemini generates a shift summary. All inside Flink. No external orchestration. When operators need interactive analysis, Gemini's function calling queries live Kafka state."

**[1:45 After alert appears — Insert]** "And watch — ML_PREDICT classifies it instantly: ENVIRONMENTAL. The classifier runs on Vertex AI, called directly from Flink SQL."

**[2:15 After Gemini response — Insert]** "And every five minutes, Flink calls Gemini via ML_PREDICT to generate a shift summary — batching all anomalies into one AI-written briefing. Not per-alert. Batched intelligence."

**[2:20 Tech Credibility — Replace]** "This runs on Confluent Cloud. Seven Kafka topics. Managed Flink running ML_DETECT_ANOMALIES and ML_PREDICT. Two Vertex AI connections from Flink SQL — a classifier for instant categorization, Gemini for periodic summaries. Plus interactive function calling for operators. Three AI touchpoints: streaming detection, streaming classification, and conversational copilot. All on Confluent plus Google Cloud."

**[2:45 Close — Replace]** "CoSense Cloud runs AI at every layer. ML_DETECT_ANOMALIES for streaming detection. ML_PREDICT for classification and summaries. Gemini for interactive analysis. All connected through Confluent Cloud and Vertex AI. That's AI on data in motion. Real-time detection. Real-time classification. Real impact."

---

# DONE. GO RECORD. 🎬
