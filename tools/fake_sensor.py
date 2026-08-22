#!/usr/bin/env python3
"""
Standalone stand-in for the Wokwi water leak sensor.

Posts the exact same JSON payload as iot/water-leak-sensor/sketch.ino to the
telemetry endpoint, so demos, videos and load checks can exercise the
auto-request rules without launching a simulator (or needing a Wokwi token).

Example:
    python3 tools/fake_sensor.py --key $CSRMS_WATER_KEY --readings 5
"""

import argparse
import json
import sys
import time
import urllib.error
import urllib.request


def post(base, path, key, payload):
    req = urllib.request.Request(
        f"{base}{path}",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "X-Device-Key": key},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status
    except urllib.error.HTTPError as exc:
        return exc.code


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="http://127.0.0.1:8000")
    parser.add_argument("--key", required=True, help="device key printed by seed_demo")
    parser.add_argument("--sensor", choices=["water", "network", "fire"], default="water")
    parser.add_argument("--device-id", default=None)
    parser.add_argument("--location", default="Residence C · geyser room")
    parser.add_argument("--readings", type=int, default=4)
    parser.add_argument("--interval", type=float, default=2.0)
    parser.add_argument("--from", dest="low", type=float, default=35.0,
                        help="first reading value (moisture percent)")
    parser.add_argument("--to", dest="high", type=float, default=88.0,
                        help="last reading value; crosses the 60 percent threshold")
    args = parser.parse_args()

    paths = {"water": "/api/telemetry/water/", "network": "/api/telemetry/network/", "fire": "/api/telemetry/fire/"}
    device_id = args.device_id or {"water": "water-01", "network": "net-01", "fire": "fire-01"}[args.sensor]

    for index in range(args.readings):
        fraction = index / max(args.readings - 1, 1)
        value = round(args.low + (args.high - args.low) * fraction, 1)
        payload = {
            "moisture_percent": value,
            "location": args.location,
            "device_id": device_id,
        }
        if args.sensor == "network":
            payload = {
                "reachable": value < 50,  # reuse the ramp: late readings "fail"
                "latency_ms": int(value),
                "location": args.location,
                "device_id": device_id,
            }
        elif args.sensor == "fire":
            payload = {
                "smoke_level": int(value // 2),
                "temperature_c": value,
                "location": args.location,
                "device_id": device_id,
            }

        status = post(args.base, paths[args.sensor], args.key, payload)
        print(f"{time.strftime('%H:%M:%S')} {device_id} {args.sensor} reading {value} -> HTTP {status}", flush=True)
        if index < args.readings - 1:
            time.sleep(args.interval)

    return 0


if __name__ == "__main__":
    sys.exit(main())
