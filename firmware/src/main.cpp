#include <Arduino.h>
#include <DallasTemperature.h>
#include <OneWire.h>

// Create include/config.h from config.example.h before flashing a device.
#include "config.h"

namespace {
OneWire oneWire(DS18B20_PIN);
DallasTemperature sensor(&oneWire);
unsigned long lastSampleAt = 0;

void enqueueOfflineRecord(float rawTemperature, bool sensorOk) {
  // TODO: Persist a bounded FIFO in NVS/Preferences. Do not overwrite records
  // silently; retain a dropped-record counter for observability.
}

bool sendTelemetry(float rawTemperature, float correctedTemperature, bool sensorOk) {
  // TODO: Wi-Fi reconnect with backoff, POST JSON to /api/telemetry and accept
  // only HTTP 200/201 as confirmation. Include buffered_records in the payload.
  return false;
}

void sampleAndReport() {
  sensor.requestTemperatures();
  const float rawTemperature = sensor.getTempCByIndex(0);
  const bool sensorOk = rawTemperature != DEVICE_DISCONNECTED_C && rawTemperature > -55 && rawTemperature < 85;
  // TODO: Load OFFSET_TEMP from Preferences and apply it only for valid readings.
  const float correctedTemperature = rawTemperature;

  if (!sendTelemetry(rawTemperature, correctedTemperature, sensorOk)) {
    enqueueOfflineRecord(rawTemperature, sensorOk);
  }
}
}  // namespace

void setup() {
  Serial.begin(115200);
  sensor.begin();
  // TODO: initialize Preferences, Wi-Fi and bounded offline queue.
}

void loop() {
  const unsigned long now = millis();
  if (now - lastSampleAt >= SAMPLE_INTERVAL_MS) {
    lastSampleAt = now;
    sampleAndReport();
  }
}
