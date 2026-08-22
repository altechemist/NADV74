// CSRMS network monitor - simulated ESP32 device.
//
// Every five minutes it checks whether the campus gateway can be reached and
// posts the result to /api/telemetry/network/. The backend counts consecutive
// failures and raises an IT Support request after three in a row.
//
// Before running: put your WiFi details and the device key printed by
// `python manage.py seed_demo` in the defines below (or in secrets.h).

#include <WiFi.h>
#include <HTTPClient.h>

const char *WIFI_SSID = "Wokwi-GUEST";
const char *WIFI_PASSWORD = "";

// Paste the key issued for this sensor by the backend seed command.
#define DEVICE_KEY "paste-network-device-key-here"

const char *API_URL = "http://192.168.1.100:8000/api/telemetry/network/";
const char *DEVICE_ID = "net-01";
const char *LOCATION = "Campus core switch";

// Report cadence: 5 minutes as per the design document. Shortened here so a
// demo shows results quickly; set back to 300000UL for the real thing.
const unsigned long REPORT_INTERVAL_MS = 30000UL;

void setup() {
  Serial.begin(115200);
  connectWifi();
}

void loop() {
  static unsigned long lastReport = 0;
  if (millis() - lastReport < REPORT_INTERVAL_MS) {
    return;
  }
  lastReport = millis();

  if (WiFi.status() != WL_CONNECTED) {
    connectWifi();
  }

  bool reachable = pingGateway();
  int latencyMs = reachable ? random(8, 60) : 0;

  postReading(reachable, latencyMs);
}

void connectWifi() {
  Serial.print("Connecting to WiFi");
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(250);
    Serial.print(".");
  }
  Serial.println(" connected.");
}

// Stands in for an ICMP ping. Roughly one check in six fails so the demo
// eventually trips the three-failure rule without waiting all day.
bool pingGateway() {
  return random(0, 6) != 0;
}

void postReading(bool reachable, int latencyMs) {
  HTTPClient http;
  http.begin(API_URL);
  http.addHeader("Content-Type", "application/json");
  // Devices authenticate with their own key, never a user login.
  http.addHeader("X-Device-Key", DEVICE_KEY);

  String payload = String("{\"reachable\":") + (reachable ? "true" : "false") +
                   ",\"latency_ms\":" + latencyMs +
                   ",\"location\":\"" + LOCATION + "\"" +
                   ",\"device_id\":\"" + DEVICE_ID + "\"}";

  int code = http.POST(payload);
  Serial.printf("Network check %s (%d ms) -> HTTP %d\n",
                reachable ? "OK" : "FAILED", latencyMs, code);
  http.end();
}
