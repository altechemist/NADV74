---
marp: true
theme: default
paginate: true
size: 16:9
style: |
  section { background: #f5f0e8; color: #1c2b2e; font-family: Georgia, serif; }
  h1 { color: #102a35; }
  h2 { color: #102a35; }
  strong { color: #a06b1f; }
  table { font-size: 0.8em; }
  img { border-radius: 10px; box-shadow: 0 6px 24px rgba(16,42,53,.18); }
  section.lead { background: #102a35; color: #f5f0e8; }
  section.lead h1 { color: #e6a649; }
---

<!-- _class: lead -->

# CSRMS
## Campus Service Request Management System

NADV 744 · Advanced Development Systems · Group Assignment 2026
Sol Plaatje University

*(team names + student numbers)*

---

# The problem

- Campus maintenance runs on WhatsApp and hallway conversations
- Reports arrive without structure: no category, no location, no owner
- Nobody can answer: *how many problems, how long to fix, which buildings?*
- Some failures **should not depend on a human noticing** — leaks and overheating
  happen at 2am

---

# What we built

One system, two ways in:

- Students log problems → staff resolve them through a managed workflow
- Simulated IoT sensors raise requests **on their own** when conditions demand it

![w:1100](../diagrams/architecture.png)

---

# How a request travels

![w:1150](../diagrams/dataflow.png)

Every path — student report or sensor reading — ends in the same audited workflow:
`PENDING → ASSIGNED → IN_PROGRESS → RESOLVED`

---

# Security model

| Layer | Decision |
|---|---|
| Auth | JWT on every endpoint (register/login/refresh excepted) |
| Roles | STUDENT / STAFF / ADMIN — registration always creates STUDENT, server-side |
| Objects | A student who guesses another's request ID gets a **404**, proven by tests |
| Devices | Per-sensor keys, SHA-256 hashed, type-bound, individually revocable |
| Passwords | Django validators + PBKDF2 |

---

# IoT auto-request rules

| Sensor | Cadence | Trigger | Ticket raised |
|---|---|---|---|
| Network monitor | 5 min | 3 consecutive failed pings | IT Support · HIGH |
| Water leak | 2 min | moisture > 60% | Facilities · HIGH |
| Fire/smoke | 10 s | smoke ≥ 40 or temp ≥ 50 °C | Safety · CRITICAL |

Open SYSTEM tickets are **deduplicated** per sensor+location — a stuck sensor
raises one ticket, not a hundred.

---

<!-- _class: lead -->

# Live demo

*Student report → staff workflow → sensor-triggered ticket*

---

# Student view

![w:1150](../screenshots/02-student-overview.png)

---

# Staff workflow with full history

![w:1150](../screenshots/06-request-detail-workflow.png)

---

# Live sensor telemetry

![w:1150](../screenshots/07-sensor-charts.png)

---

# Testing & evaluation

- **59 automated API/service tests** — every security claim has a negative test
- Firmware: structural validation + Wokwi scenarios driving sensors to their limits
- Playwright walkthrough of all three roles doubles as the screenshot generator
- Performance (50 rounds/endpoint): **p95 under 8 ms** on all reads;
  JWT checks are DB-free, lists are paginated

---

# Limitations & future work

Honest limits: simulated hardware · pull-only notifications · laptop-scale perf data

Next, in order:
1. Email/push notifications with staff digests
2. SLA tracking and automatic escalation
3. Real ESP32 hardware (same sketches, new WiFi credentials)
4. MySQL deployment behind HTTPS

---

# One workflow, recorded end to end

<video src="assets/csrms-demo.mp4" controls muted style="width: 100%; max-height: 78vh; border-radius: 12px;"></video>

Student report → staff triage → simulated sensor trips → SYSTEM ticket. Same file: `docs/demo/assets/csrms-demo.mp4`

---

<!-- _class: lead -->

# Thank you

github.com/*your-org*/NADV74

`README.md` → running everything in three commands
