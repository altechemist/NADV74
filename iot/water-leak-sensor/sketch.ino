// CSRMS water leak sensor - simulated ESP32 device.
//
// Every two minutes it reads a moisture probe (a potentiometer stands in for
// the probe in Wokwi) and posts the percentage to /api/telemetry/water/.
// Readings above the configured threshold make the backend raise a Facilities
// request automatically.
//
// Turn the potentiometer up past ~60% to simulate a leaking geyser.

#include <WiFi.h>
#include <HTTPClient.h>

const char *WIFI_SSID = "Wokwi-GUEST";
const char *WIFI_PASSWORD = "";

// Paste the key issued for this sensor by the backend seed command.
#define DEVICE_KEY "paste-water-device-key-here"

const char *API_URL = "http://192.168.1.100:8000/api/telemetry/water/";
const char *DEVICE_ID = "water-01";
const char *LOCATION = "Residence C · geyser room";

const int MOISTURE_PIN = 34;

// Report cadence: 2 minutes per the design document; shortened for demos.
const unsigned long REPORT_INTERVAL_MS = 20000UL;

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

  // The ADC returns 0-4095; map that onto a 0-100% moisture scale.
  int raw = analogRead(MOISTURE_PIN);
  int moisturePercent = map(raw, 0, 4095, 0, 100);

  postReading(moisturePercent);
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

void postReading(int moisturePercent) {
  HTTPClient http;
  http.begin(API_URL);
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-Device-Key", DEVICE_KEY);

  String payload = String("{\"moisture_percent\":") + moisturePercent +
                   ",\"location\":\"" + LOCATION + "\"" +
                   ",\"device_id\":\"" + DEVICE_ID + "\"}";

  int code = http.POST(payload);
  Serial.printf("Moisture %d%% -> HTTP %d\n", moisturePercent, code);
  http.end();
}
