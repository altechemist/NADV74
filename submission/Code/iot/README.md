# IoT sensor simulations (Wokwi)

Three virtual ESP32 devices feed the CSRMS telemetry service. No physical
hardware is required — each folder is a self-contained Wokwi project:

| File | Purpose |
|---|---|
| `sketch.ino` | Firmware source |
| `diagram.json` | Circuit / wiring |
| `wokwi.toml` | Points Wokwi at the compiled firmware |
| `platformio.ini` | Build config so `pio run` compiles the sketch headlessly |
| `scenario.yaml` | Automated test: drives sensors and asserts serial output |

| Folder | Sensor | Cadence | Auto-request rule (server side) |
|---|---|---|---|
| `network-monitor/` | Gateway reachability + latency | every 5 min | 3 consecutive failures → IT Support / HIGH |
| `water-leak-sensor/` | Moisture % near pipes | every 2 min | above threshold → Facilities / HIGH |
| `fire-smoke-sensor/` | Smoke level + temperature | continuous (10 s) | smoke OR temperature over threshold → Safety / CRITICAL |

## Running in VS Code (recommended)

1. Open this repository in VS Code. You will be prompted to install the
   recommended extensions (Wokwi + PlatformIO) — accept.
2. Start the Django API (`python manage.py runserver`) and run
   `python manage.py seed_demo` once; it prints one device key per sensor.
3. In a device folder, edit `sketch.ino`:
   - `DEVICE_KEY` — the key printed in step 2 (never commit a real key)
   - `API_URL` — your machine's LAN IP, e.g. `http://192.168.1.100:8000/api/telemetry/network/`
     (`127.0.0.1` will not work from the simulator sandbox)
4. Compile: **Terminal → Run Task** or `pio run` inside the device folder.
5. Press **F1 → "Wokwi: Start Simulator"** and watch the serial monitor.

The same folders open unchanged on [wokwi.com](https://wokwi.com) if you
prefer the browser editor.

## Scripts and tests

From `iot/` (requires the [`wokwi-cli`](https://docs.wokwi.com/wokwi-ci/cli-installation)
binary on PATH, PlatformIO Core for compiling, and `WOKWI_CLI_TOKEN` for anything
that runs a simulation):

```sh
npm run check          # structural validation - no token or tooling needed
npm run lint           # validate all three diagram.json files
npm run compile        # build all three firmwares with PlatformIO
npm run sim:network    # run one simulation and stream serial output
npm run test           # structural checks + compile + all three scenarios
```

The scenario files are real automated tests: they turn the water potentiometer
to 90%, heat the DHT22 to 60 °C, let the network monitor complete a report
cycle, and assert the expected serial output. They deliberately do not require
the backend to be reachable — end-to-end behaviour (device key auth, thresholds,
auto-created requests) is covered by the Django test suite instead.

To see a sensor actually raise a ticket, run the backend locally, point
`API_URL` at your LAN IP, expect `HTTP 201` in the serial monitor, then check
the request queue as staff.

## Triggering alerts by hand

- **Network:** failures are randomised (~1 in 6); three in a row raise a ticket.
- **Water:** turn the potentiometer past ~60% to simulate a leak.
- **Fire/smoke:** raise the MQ-2 slider or heat the DHT22 past 50 °C.

The firmware only reports readings — threshold checking and request creation
happen server-side so the rules stay in one place and apply to any device.
