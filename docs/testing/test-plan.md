# CSRMS — Test Plan and Results

Module: NADV 744 Group Assignment 2026
Last run: 21 August 2026 — **59 tests, all passing** (`python manage.py test`, Django 6 / Python 3.14)

## 1. Scope and objectives

The system has three surfaces that can fail in different ways:

1. **The REST API** — authentication, role-based access and the request workflow.
2. **The telemetry ingest service** — device-key authentication and the rules that turn sensor readings into service requests.
3. **The simulated IoT devices** — firmware that must boot, join WiFi and post readings on schedule.

The objective of testing is to prove that unauthorised access is impossible (including by guessing IDs), that the request workflow only follows legal transitions, that every state change leaves an audit trail, and that each IoT rule fires exactly once per incident.

## 2. Approach

| Layer | Technique | Tooling |
|---|---|---|
| API units | `APITestCase` suites per app, real SQLite database per run | Django test runner |
| Permissions | Positive *and* negative cases for every role on every endpoint | same |
| Telemetry rules | Readings posted through the full view → service → model stack | same |
| IoT firmware | Wokwi automation scenarios asserting serial output; structural validation without credentials | `wokwi-cli`, `scenario.yaml` |
| End-to-end smoke | Playwright drives the real frontend against the live API (login, dashboards, request actions) and captures screenshots | Node/Playwright |
| Performance | Scripted load probe measuring latency percentiles per endpoint family | `tools/perf_check.py` |

Tests live next to the code they cover: `backend/apps/<app>/tests.py`.

## 3. Test matrix

### Accounts and authentication — 14 tests

| Area | Representative cases |
|---|---|
| Registration | creates STUDENT account; ignores any role submitted by the client; duplicate username rejected; weak password rejected |
| Credential storage | password stored as PBKDF2 hash, never plaintext |
| Login / tokens | login returns access + refresh + profile; wrong password rejected; refresh rotates tokens; logout blacklists the refresh token |
| Profile | `/auth/me/` requires auth; returns and updates profile |
| Administration | user list admin-only; admin creates staff accounts; delete deactivates instead of removing |

### Request workflow — 22 tests

| Area | Representative cases |
|---|---|
| Visibility | student lists only own requests; staff/admin see everything; student cannot read another student's request by guessing its ID |
| Creation | student creates request; creation logged as first history entry |
| Status workflow | `PENDING → ASSIGNED → IN_PROGRESS → RESOLVED` accepted; illegal transitions rejected; every change logged with timestamp and comment |
| Assignment | assignment moves PENDING → ASSIGNED and logs; cannot assign to a student; student cannot assign |
| Comments | owner can comment; other students cannot comment or read history |
| Editing / cancellation | owner edits own PENDING request; editing blocked once work started; owner cancels PENDING; RESOLVED cannot be cancelled |
| Categories | any authenticated user lists; admin-only creation |

### Telemetry and device keys — 19 tests

| Area | Representative cases |
|---|---|
| Key auth | missing key rejected; unknown key rejected; revoked key rejected; a user JWT is not accepted on telemetry endpoints |
| Key binding | key bound to one sensor type cannot post to another; unknown sensor endpoint returns 404 |
| Ingest | valid network reading stored; malformed payload rejected with field errors |
| Network rule | 3 consecutive failures raise one HIGH IT Support request; a success resets the streak; no duplicate while ticket open; new ticket allowed after previous resolved |
| Water rule | moisture below threshold does nothing; above threshold raises HIGH Facilities request; repeated breaches do not duplicate |
| Fire rule | smoke alone raises CRITICAL Safety request; temperature alone does too |
| Workflow parity | auto-created (SYSTEM) request follows exactly the same workflow as manual ones |

### Dashboard — 4 tests

Authentication required; student counts scoped to own requests; staff counts cover campus; notifications visible only to their recipient.

## 4. IoT firmware scenarios

Each device folder carries a `scenario.yaml` executed by `wokwi-cli`:

- **network-monitor** — boots, joins WiFi, completes a gateway-check cycle, prints the report line.
- **water-leak-sensor** — potentiometer driven to 90% via automation control; reading posted every cycle.
- **fire-smoke-sensor** — DHT22 heated to 60 °C; full report cycle still completes.

`iot/test/validate_sketches.py` additionally checks structure without a Wokwi account: required files present, correct endpoint per sketch, no committed device keys, diagram parts match the design, scenario markers exist in the firmware.

## 5. Performance and scalability observations

Method: `tools/perf_check.py` issues timed requests against a running server (see
[`performance-results.md`](performance-results.md) for the numbers captured on the reference machine).

Findings:

- Authenticated reads sit in single-digit milliseconds at desktop scale; JWT verification is local (no database hit), which keeps `/api/dashboard/` cheap.
- List endpoints are paginated, so response time stays flat as the request table grows.
- The known scaling constraint is SQLite under concurrent writes; production configuration switches to MySQL via environment variables.
- Device-key lookups are indexed by the SHA-256 hash, so ingest cost does not grow with the number of devices.

## 6. Defect handling

Defects found during development were fixed and pinned with a regression test before moving on. Two examples worth noting:

1. Telemetry authentication initially returned 403 (forbidden) instead of 401 for missing keys — fixed by adding an authenticate header, then locked in by `test_missing_key_rejected`.
2. The network failure streak was counted across all locations; it is now scoped per device/location so an outage in one building cannot trip another building's rule.

## 7. How to reproduce

```sh
cd backend && python manage.py test          # 59 API/service tests
cd iot && npm run check                      # structural firmware checks
cd iot && npm run test                       # full Wokwi simulation scenarios*
node tools/screenshots.mjs                   # end-to-end browser walkthrough*

* needs extra tooling - see iot/README.md and tools/README.md
```
