#!/usr/bin/env python3
"""
Structural checks for the three Wokwi simulations.

This runs with nothing but the Python standard library, so it works in CI
without a Wokwi account. It does not simulate the firmware - the scenario
files (run through wokwi-cli) do that - it just catches the boring mistakes:
a missing file, a sketch pointed at the wrong endpoint, a device key that
was accidentally committed, a diagram referencing parts that no longer exist.

Usage: python3 test/validate_sketches.py   (from the iot/ directory)
"""

import json
import re
import sys
from pathlib import Path

IOT_DIR = Path(__file__).resolve().parent.parent

# Per device: which telemetry endpoint the sketch must target and which
# extra parts the diagram is expected to contain.
DEVICES = {
    "network-monitor": {
        "endpoint": "/api/telemetry/network/",
        "parts": ["wokwi-esp32-devkit-v1", "wokwi-led"],
    },
    "water-leak-sensor": {
        "endpoint": "/api/telemetry/water/",
        "parts": ["wokwi-esp32-devkit-v1", "wokwi-potentiometer"],
    },
    "fire-smoke-sensor": {
        "endpoint": "/api/telemetry/fire/",
        "parts": ["wokwi-esp32-devkit-v1", "wokwi-mq2-gas-sensor", "wokwi-dht22"],
    },
}

REQUIRED_FILES = [
    "sketch.ino",
    "diagram.json",
    "wokwi.toml",
    "platformio.ini",
    "scenario.yaml",
]

# A pasted seed_demo key is 48 random characters; the placeholder is short
# and obviously named. Anything key-shaped in git history would be a leak.
KEY_PLACEHOLDER = re.compile(r'#define DEVICE_KEY "[a-z0-9-]*key-here"')
SUSPICIOUS_KEY = re.compile(r'#define DEVICE_KEY "([A-Za-z0-9_]{20,})"')


def check(device_name, spec, failures):
    folder = IOT_DIR / device_name

    def fail(msg):
        failures.append(f"{device_name}: {msg}")

    for required in REQUIRED_FILES:
        if not (folder / required).is_file():
            fail(f"missing {required}")

    sketch_path = folder / "sketch.ino"
    if not sketch_path.is_file():
        return

    sketch = sketch_path.read_text()

    if not KEY_PLACEHOLDER.search(sketch):
        fail('DEVICE_KEY must stay a placeholder in git; paste real keys locally only')
    if SUSPICIOUS_KEY.search(sketch):
        fail("sketch appears to contain a committed device key")

    if f'API_URL = "{spec["endpoint"]}"' not in sketch.replace("'", '"').replace(
        'API_URL = "', 'API_URL = "'
    ):
        # tolerate quote style, but the path itself must be exact
        if spec["endpoint"] not in sketch:
            fail(f'sketch does not post to {spec["endpoint"]}')

    for header in ("X-Device-Key", "Content-Type"):
        if header not in sketch:
            fail(f"sketch never sends the {header} header")

    diagram_path = folder / "diagram.json"
    if diagram_path.is_file():
        try:
            diagram = json.loads(diagram_path.read_text())
            part_types = [part.get("type") for part in diagram.get("parts", [])]
            for expected in spec["parts"]:
                if expected not in part_types:
                    fail(f"diagram.json is missing a {expected} part")
        except json.JSONDecodeError as exc:
            fail(f"diagram.json is not valid JSON ({exc})")

    scenario_path = folder / "scenario.yaml"
    if scenario_path.is_file():
        scenario = scenario_path.read_text()
        if "steps:" not in scenario or "wait-serial" not in scenario:
            fail("scenario.yaml has no steps to assert serial output")
        else:
            # every quoted serial marker in the scenario should also appear
            # in the sketch, otherwise the test can never pass
            for marker in re.findall(r"wait-serial: '([^']+)'", scenario):
                if marker not in sketch:
                    fail(f"scenario waits for {marker!r} but the sketch never prints it")


def main():
    failures = []
    for device_name, spec in DEVICES.items():
        check(device_name, spec, failures)

    if failures:
        print(f"FAILED - {len(failures)} problem(s):")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    print(f"All {len(DEVICES)} simulation projects look structurally sound.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
