# Performance Results — CSRMS API

Captured 21 August 2026 against a locally seeded development database
(`seed_demo` data: 6 categories, 3 accounts, ~10 requests) using
`tools/perf_check.py` — 50 timed requests per endpoint, admin session.

**Environment:** Python 3.14 / Django 6 on Linux, SQLite in development mode,
server and probe on the same machine (loopback, so numbers exclude real network time).

| Endpoint | Rounds | Mean | p50 | p95 | Max |
|---|---|---|---|---|---|
| `/api/requests/` List requests | 50 | 4.8 ms | 4.2 ms | 7.4 ms | 8.4 ms |
| `/api/dashboard/` Dashboard summary | 50 | 4.7 ms | 4.7 ms | 5.9 ms | 6.6 ms |
| `/api/notifications/` Notifications | 50 | 3.7 ms | 3.5 ms | 5.0 ms | 7.5 ms |
| `/api/categories/` Categories | 50 | 4.1 ms | 3.8 ms | 5.9 ms | 9.5 ms |
| `/api/users/` User directory | 50 | 4.6 ms | 4.4 ms | 6.5 ms | 8.1 ms |

## Reading the numbers

- Every authenticated read answers in single-digit milliseconds at p95. JWT
  verification is cryptographic and local — it never touches the database — so
  per-request authorisation overhead stays flat regardless of load.
- The dashboard endpoint aggregates counts across several tables yet costs no
  more than plain list endpoints at this scale; its queries are count/filter
  operations that SQLite handles comfortably.
- List endpoints are paginated, so response cost is bounded by page size rather
  than table size: doubling the number of requests in the system does not double
  list latency.

## Known limits

- **SQLite writes are serialised.** Under concurrent telemetry ingest plus user
  traffic, write contention would appear before read latency does. The shipped
  settings switch to MySQL through environment variables for deployment for
  exactly this reason.
- **Loopback measurements flatter the network hop.** A campus deployment adds
  LAN round-trip time (typically 1–5 ms), which dwarfs these server-side costs.
- The probe measures reads only; telemetry ingest was exercised functionally by
  the test suite rather than under synthetic load.

## Reproducing

```sh
cd backend && source ../venv/bin/activate
python manage.py migrate && python manage.py seed_demo
python manage.py runserver            # terminal 1
python3 tools/perf_check.py --n 50    # terminal 2, from the repo root
```
