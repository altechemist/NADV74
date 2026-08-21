#!/usr/bin/env python3
"""
Latency probe for the CSRMS API.

Logs in once, then hits each read endpoint N times and reports mean / p50 /
p95 / max latency per endpoint family. Standard library only - no extra
packages needed on the machine taking the measurements.

Typical use (server running on localhost):

    python3 tools/perf_check.py --n 50
    python3 tools/perf_check.py --n 100 --out docs/testing/performance-results.md

The numbers this produces end up in the report's evaluation section, so keep
the environment honest: run against a freshly seeded database and note the
machine specs alongside the results.
"""

import argparse
import json
import statistics
import sys
import time
import urllib.error
import urllib.request

DEFAULT_BASE = "http://127.0.0.1:8000"
DEFAULT_USER = "admin"
DEFAULT_PASSWORD = "Campus#2026"

# label, method, path, needs_admin
ENDPOINTS = [
    ("List requests", "GET", "/api/requests/", False),
    ("Dashboard summary", "GET", "/api/dashboard/", False),
    ("Notifications", "GET", "/api/notifications/", False),
    ("Categories", "GET", "/api/categories/", False),
    ("User directory", "GET", "/api/users/", True),
]


def request_json(url, data=None, token=None, method=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode() if data is not None else None,
        headers=headers,
        method=method or ("POST" if data is not None else "GET"),
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        body = resp.read()
    return json.loads(body) if body else {}


def login(base, username, password):
    return request_json(f"{base}/api/auth/login/", {"username": username, "password": password})["access"]


def percentile(values, pct):
    """Nearest-rank percentile; good enough for a small sample."""
    ordered = sorted(values)
    idx = max(0, min(len(ordered) - 1, round(pct / 100 * len(ordered) + 0.5) - 1))
    return ordered[idx]


def measure(base, token, is_admin, rounds):
    rows = []
    for label, method, path, needs_admin in ENDPOINTS:
        if needs_admin and not is_admin:
            continue
        timings = []
        for _ in range(rounds):
            start = time.perf_counter()
            try:
                request_json(f"{base}{path}", token=token, method=method)
            except urllib.error.HTTPError as exc:
                # 404 on an empty table is still a valid timing sample for a
                # smoke probe, but flag it so the numbers aren't misread.
                print(f"  ! {label} returned HTTP {exc.code}", file=sys.stderr)
            elapsed_ms = (time.perf_counter() - start) * 1000
            timings.append(elapsed_ms)
        rows.append((label, path, timings))
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default=DEFAULT_BASE)
    parser.add_argument("--user", default=DEFAULT_USER)
    parser.add_argument("--password", default=DEFAULT_PASSWORD)
    parser.add_argument("--n", type=int, default=30, help="requests per endpoint")
    parser.add_argument("--out", help="write a markdown results table to this file")
    args = parser.parse_args()

    print(f"Logging in as {args.user} at {args.base} ...")
    try:
        token = login(args.base, args.user, args.password)
    except (urllib.error.URLError, KeyError) as exc:
        sys.exit(f"Could not log in: {exc}. Is the server running and seeded?")

    print(f"Probing {len(ENDPOINTS)} endpoints x {args.n} rounds ...\n")
    rows = measure(args.base, token, is_admin=True, rounds=args.n)

    header = f"| Endpoint | Rounds | Mean | p50 | p95 | Max |\n|---|---|---|---|---|---|"
    lines = [header]
    for label, path, timings in rows:
        lines.append(
            f"| `{path}` {label} | {len(timings)} | {statistics.mean(timings):.1f} ms "
            f"| {percentile(timings, 50):.1f} ms | {percentile(timings, 95):.1f} ms "
            f"| {max(timings):.1f} ms |"
        )
    table = "\n".join(lines)
    print(table)

    if args.out:
        with open(args.out, "w") as fh:
            fh.write(table + "\n")
        print(f"\nSaved to {args.out}")


if __name__ == "__main__":
    main()
