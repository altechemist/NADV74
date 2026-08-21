# CSRMS live demo script

Target length: **8–10 minutes** plus questions. Rehearse it once end-to-end before
demo day; the examiner asks questions *during* the demo, so know the material well
enough to talk while clicking.

## Before the audience arrives

1. Backend running: `cd backend && source ../venv/bin/activate && python manage.py runserver`
2. Frontend running: `cd frontend && npm run dev` → open http://localhost:3000
3. Fresh-ish data: `python manage.py seed_demo` is idempotent — safe to run again.
4. Wokwi open in a browser tab with the **water leak sensor** project loaded
   (`iot/water-leak-sensor/`), device key pasted into `DEVICE_KEY`, `API_URL`
   pointed at your LAN IP.
5. Postman open with the collection imported (fallback if the network misbehaves).
6. Terminal spare, in `backend/`, for `manage.py shell` moments.

Credentials: `naledi` (student) · `lerato` (staff) · `admin` (password `Campus#2026`).

## Act 1 — The problem becomes a ticket (student) · ~2 min

1. Log in as **naledi**. Point out the personal counters — students only ever see
   their own world.
2. Open **Requests**, click an existing request, show the history timeline:
   *"every state change is logged with who, when and why."*
3. Click **Log a request**, submit a new one (e.g. "Printer out of toner in Lab 4",
   Equipment / MEDIUM). Show it appears as PENDING.

Talking point: registration always creates STUDENT accounts server-side — try to
convince the audience you can't self-elevate to ADMIN by tampering with the form.

## Act 2 — The workflow (staff) · ~2 min

1. Log out, log in as **lerato**. Note the wider view: staff see everything.
2. Find naledi's new request. **Assign** it to yourself → status ASSIGNED, history
   entry written, notification generated for naledi.
3. Move it **IN_PROGRESS**, then **RESOLVED**, each with a comment.
4. Try an illegal jump for the audience (open DevTools → fetch against the API, or
   just explain): PENDING → RESOLVED directly is rejected by the service layer.

Talking point: transitions are validated in one service layer shared by the API,
the seed command *and* the IoT rules — there is no side door.

## Act 3 — Sensors that raise their own tickets · ~3 min

1. In the staff session, open **Sensors** — show twelve hours of chart history.
2. Switch to the Wokwi tab, run the water simulation, drag the potentiometer past
   60%.
3. Watch the serial monitor print `Moisture 87% -> HTTP 201`.
4. Back in CSRMS (still lerato): refresh requests — a **SYSTEM / Facilities /
   HIGH** ticket appeared. Open it: same workflow, same history, source SYSTEM.
5. Post another high reading: *no duplicate ticket* — explain dedupe keys.
6. If time allows: fire sensor DHT22 slider past 50 °C → CRITICAL Safety ticket.

Talking point: device keys are hashed at rest, bound to one endpoint each, and
revocable individually. A user JWT is worthless here — the test suite proves it.

## Act 4 — Administration and evidence · ~1.5 min

1. Log in as **admin**, show **People** (create/deactivate accounts) and campus-wide
   dashboard counters.
2. Show the GitHub repo briefly: commit history, README quick-start, test plan,
   performance results.
3. Close with the numbers: **59 passing tests**, p95 under 8 ms on all reads,
   three automated firmware scenarios.

## Likely questions (and short answers)

| Question | Answer |
|---|---|
| How do you stop a stuck sensor flooding the queue? | Dedupe key per sensor+location; one open SYSTEM ticket at a time; new one only after resolve/cancel. |
| What if a device key leaks? | Revoke that one key; users unaffected; database stores only SHA-256 hashes so nothing to reverse. |
| Can a student read someone else's request? | No — object-level permission returns 404 even with a guessed ID; covered by a named test. |
| Why Django REST Framework? | Batteries-included serialisation, auth, permissions and browsable API; lets us spend time on domain logic. |
| Where does it scale first? | SQLite write concurrency; settings switch to MySQL via env vars. Reads are paginated and JWT checks are DB-free. |
| What happens if the backend is down when a sensor posts? | The sketch logs the HTTP error and retries next cycle; readings are transient, rules re-evaluate on the next successful post. |
| Real hardware? | Same sketches run on a real ESP32 — change WiFi SSID/key and API URL. |

## Fallback plan

If Wokwi or the LAN fails live: Postman through the telemetry endpoints with the
device key shows HTTP 201s and tickets appearing; screenshots in
`docs/screenshots/` back everything up.
