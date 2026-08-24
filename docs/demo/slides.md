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

Karabelo Nthoroane · 202328762<br>
Khulani Hlebeya · 202302091<br>
Kegomoditswe Mongale · 201718863<br>
Metswi kabo · 202104098

<!-- Four of us built CSRMS for this module. The problem: campus maintenance runs on WhatsApp and people bumping into each other in hallways. Nothing gets logged, so requests slip through. And some things — a leaking pipe at 2am, a server room overheating — nobody is around to report. We wanted one system that handles both. -->

---

# The problem

- Campus maintenance runs on WhatsApp and hallway conversations
- Reports arrive without structure: no category, no location, no owner
- Nobody can answer: _how many problems, how long to fix, which buildings?_
- Some failures **should not depend on a human noticing** — leaks and overheating
  happen at 2am

<!-- Picture this: a geyser bursts in a residence at midnight. Nobody is there to report it. By morning the damage is done. Or IT finds out about a network outage from students tweeting about it. Right now there is no structure — a student tells a lecturer, the lecturer sends a WhatsApp, maybe it gets forgotten. We wanted to fix that: give students a place to log things, and give sensors a way to speak up when nobody is watching. -->

---

# What we built

One system, two ways in:

- Students log problems → staff resolve them through a managed workflow
- Simulated IoT sensors raise requests **on their own** when conditions demand it

![w:1100](../diagrams/architecture.png)

<!-- Look at the diagram. Left side is the human flow — students log in, submit requests, staff pick them up and work through the workflow. Right side is the IoT flow — three sensors post readings to the same API. When a threshold trips, the backend creates a ticket in the same table staff already look at. The important thing: sensors are not a separate system. They are just another API client. A sensor ticket follows the exact same path as a student report. -->

---

# How a request travels

![w:1150](../diagrams/dataflow.png)

Every path — student report or sensor reading — ends in the same audited workflow:
`PENDING → ASSIGNED → IN_PROGRESS → RESOLVED`

<!-- Two ways in, same pipeline. Student logs in, gets a JWT, submits a request — API validates it, stamps it PENDING, writes the first history entry. Staff see it, assign it, work it, resolve it. Every change gets logged with a timestamp and a comment. Sensors do the same thing: post a reading with their device key, backend checks the rule, creates a SYSTEM request if the threshold is hit. From there, same workflow. -->

---

# Security evidence

- Deliberate wrong-password login returns **HTTP 401** and grants no session
- A valid login returns JWT access and refresh tokens
- Students cannot read another student's request, even with a guessed ID
- A user JWT cannot post telemetry; sensors require a type-bound `X-Device-Key`
- Postman provides a visible API fallback for login, telemetry, and deduplication

<!-- We can back up every security claim. Wrong password? 401, no session. Students can't see each other's tickets — guess an ID, you get 404. A user JWT is useless for posting sensor data; that needs a device key. We will demo all of this. Postman is there as a backup if the browser misbehaves. -->

---

# Security model

| Layer     | Decision                                                                   |
| --------- | -------------------------------------------------------------------------- |
| Auth      | JWT on every endpoint (register/login/refresh excepted)                    |
| Roles     | STUDENT / STAFF / ADMIN — registration always creates STUDENT, server-side |
| Objects   | A student who guesses another's request ID gets a **404**, proven by tests |
| Devices   | Per-sensor keys, SHA-256 hashed, type-bound, individually revocable        |
| Passwords | Django validators + PBKDF2                                                 |

<!-- Five layers. JWT on everything except register and login. Three roles — and registration always makes a STUDENT account, no matter what you submit. Object permissions mean a student guessing IDs gets nothing. Device keys are hashed, bound to one sensor type, and you can revoke any key individually. Passwords use Django's validators plus PBKDF2. -->

---

# IoT auto-request rules

| Sensor          | Cadence | Trigger                    | Ticket raised     |
| --------------- | ------- | -------------------------- | ----------------- |
| Network monitor | 5 min   | 3 consecutive failed pings | IT Support · HIGH |
| Water leak      | 2 min   | moisture > 60%             | Facilities · HIGH |
| Fire/smoke      | 10 s    | smoke ≥ 40 or temp ≥ 50 °C | Safety · CRITICAL |

Open SYSTEM tickets are **deduplicated** per sensor+location — a stuck sensor
raises one ticket, not a hundred.

Network, water, and fire/smoke triggers are verified by the backend tests and can be
demonstrated live or through Postman when Wokwi or the network is unavailable.

<!-- Three sensors, three rules. Network monitor pings the gateway every 5 minutes — three fails in a row and it raises an IT Support ticket. Water leak checks moisture every 2 minutes — over 60% and Facilities gets a ticket. Fire sensor runs nonstop — smoke above 40 or temp above 50 Celsius, Safety ticket at CRITICAL. The trick is deduplication: if a sensor keeps tripping, you only get one open ticket, not a flood. A new one shows up only after the last one is resolved or cancelled. All thresholds come from environment variables, and the test suite covers all three rules. -->

---

<!-- _class: lead -->

# Live demo

_Student report → staff workflow → sensor-triggered ticket_

<!-- Let's do the live demo. One story: student reports a problem, staff works through it, sensor trips and raises its own ticket. Same workflow both ways. Logins: naledi (student), lerato (staff), admin — password Campus#2026. -->

---

# Student view

![w:1150](../screenshots/02-student-overview.png)

<!-- Logged in as naledi. See the counters at the top — students only see their own stuff. They cannot see anyone else's requests. From here they can go to Requests, log a new one, or check notifications. Try guessing another student's request ID and you get a 404. There is a test that proves it. -->

---

# Staff workflow with full history

![w:1150](../screenshots/06-request-detail-workflow.png)

<!-- Staff see everything. Open a request and you get the full picture: title, description, category, priority, location, status. The timeline at the bottom shows every change — who did what and when. Assign it, move it forward, resolve it. One thing: you cannot skip steps. PENDING straight to RESOLVED gets rejected. The same service layer backs the API, the seed command, and the IoT rules — no side door. -->

---

# Live sensor telemetry

![w:1150](../screenshots/07-sensor-charts.png)

<!-- Twelve hours of sensor history on one page — network, moisture, smoke and temperature. During the demo we flip to Wokwi, run the water sim, drag the potentiometer past 60%. You see HTTP 201 on the serial monitor. Back in CSRMS, a SYSTEM ticket appeared under Facilities. Post another high reading — no duplicate, dedupe key blocks it. If we have time, same thing with the fire sensor: push the DHT22 past 50 degrees, CRITICAL Safety ticket. Network monitor can be shown through Postman if Wokwi is not cooperating. -->

---

# Testing & evaluation

- **61 automated API/service tests** — every security claim has a negative test
- Firmware: structural validation + Wokwi scenarios driving sensors to their limits
- Playwright walkthrough of all three roles doubles as the screenshot generator
- Postman collection covers the API as a manual demonstration and fallback
- Performance (50 rounds/endpoint): **p95 under 8 ms** on all reads;
  JWT checks are DB-free, lists are paginated

<!-- 61 tests in Django's test suite — wrong password, object visibility, device key separation, all three sensor rules, deduplication. Every claim we made has a test trying to break it. Firmware side: a Python script validates the sketch structure, and Wokwi scenarios push the sensors past their thresholds. Playwright walks through all three roles in the browser — that is where these screenshots came from. Postman covers the API by hand. On performance, we timed every read endpoint 50 times — p95 under 8 milliseconds across the board. JWT checks do not touch the database, lists are paginated. -->

---

# Limitations & future work

Honest limits: simulated hardware · pull-only notifications · laptop-scale perf data

Next, in order:

1. Email/push notifications with staff digests
2. SLA tracking and automatic escalation
3. Real ESP32 hardware (same sketches, new WiFi credentials)
4. MySQL deployment behind HTTPS

<!-- What we did not do. Sensors are simulated — same code runs on real ESP32, we just did not have the hardware. Notifications only show up in the app, no email or push. Performance numbers are from a laptop, not a production server. If we had more time: push notifications so staff get alerted, SLA tracking to escalate stale tickets, real hardware, and MySQL behind HTTPS. The sketches need only WiFi credentials and an API URL to run on real boards. -->

---

# One workflow, recorded end to end

<video src="assets/csrms-demo.webm" controls muted style="width: 100%; max-height: 78vh; border-radius: 12px;"></video>

Student report → staff triage → simulated sensor trips → SYSTEM ticket. Same file: `docs/demo/assets/csrms-demo.webm`

<!-- Full recording of the workflow: student logs in and reports, staff picks it up and works through the statuses, sensors trip and SYSTEM tickets appear. One take, real time. File is at docs/demo/assets/csrms-demo.webm. -->

---

<!-- _class: lead -->

# Thank you

github.com/altechemist/NADV74

`README.md` → running everything in three commands

<!-- Everything is on GitHub — code, tests, docs, this deck. README gets you running in three commands. Questions? -->
