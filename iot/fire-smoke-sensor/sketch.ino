// CSRMS fire/smoke sensor - simulated ESP32 device.
//
// Checks continuously (every 10 seconds) and posts smoke concentration plus
// temperature to /api/telemetry/fire/. If either value crosses its threshold
// the backend immediately raises a CRITICAL Safety request.
//
// In Wokwi, drag the MQ-2 slider up or heat the DHT22 to trigger an alert.

#include <WiFi.h>
#include <HTTPClient.h>
#include <DHT.h>

const char *WIFI_SSID = "Wokwi-GUEST";
const char *WIFI_PASSWORD = "";

// Paste the key issued for this sensor by the backend seed command.
#define DEVICE_KEY "paste-fire-device-key-here"

const char *API_URL = "http://192.168.1.100:8000/api/telemetry/fire/";
const char *DEVICE_ID = "fire-01";
const char *LOCATION = "ICT building · server room";

const int SMOKE_PIN = 34;
const int DHT_PIN = 27;

DHT dht(DHT_PIN, DHT22);

// Continuous monitoring: a short loop keeps the demo responsive.
const unsigned long REPORT_INTERVAL_MS = 10000UL;

void setup() {
  Serial.begin(115200);
  dht.begin();
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

  // MQ-2 analog reading scaled to an arbitrary 0-100 smoke index.
  int rawSmoke = analogRead(SMOKE_PIN);
  int smokeLevel = map(rawSmoke, 0, 4095, 0, 100);

  float temperatureC = dht.readTemperature();
  if (isnan(temperatureC)) {
    Serial.println("DHT22 read failed; skipping this cycle.");
    return;
  }

  postReading(smokeLevel, temperatureC);
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

void postReading(int smokeLevel, float temperatureC) {
  HTTPClient http;
  http.begin(API_URL);
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-Device-Key", DEVICE_KEY);

  String payload = String("{\"smoke_level\":") + smokeLevel +
                   ",\"temperature_c\":" + String(temperatureC, 1) +
                   ",\"location\":\"" + LOCATION + "\"" +
                   ",\"device_id\":\"" + DEVICE_ID + "\"}";

  int code = http.POST(payload);
  Serial.printf("Smoke %d, temp %.1f C -> HTTP %d\n", smokeLevel, temperatureC, code);
  http.end();
}
