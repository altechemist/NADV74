# Tools

Standalone helper scripts. Each has its own dependencies; nothing here is
needed to run the system itself.

## Performance probe — `perf_check.py`

Times authenticated reads against a running API and reports mean / p50 / p95 /
max latency per endpoint. Python standard library only.

```sh
cd backend && python manage.py runserver        # terminal 1 (seeded)
python3 tools/perf_check.py --n 50              # terminal 2
```

Useful flags: `--base`, `--user`, `--password`, `--n`, `--out <file>` (writes a
markdown table). Results from the reference run live in
[`docs/testing/performance-results.md`](../docs/testing/performance-results.md).

## Browser walkthrough — `screenshots.mjs`

Drives the real frontend through all three roles with Playwright and saves a
screenshot at every stop to `docs/screenshots/`. Every step asserts on-screen
text first, so a clean run doubles as an end-to-end smoke test.

```sh
# prerequisites: backend + frontend dev servers running, seeded database
cd tools
npm install            # once; installs Playwright
npx playwright install chromium   # once; downloads the browser

node screenshots.mjs
```

Environment overrides: `FRONTEND_URL`, `OUT_DIR`, `CSRMS_DEMO_PASSWORD`.

The captured PNGs are committed so the report and slides can reference them;
re-run the script after any UI change to refresh them.
