#pragma once

// Copiar como config.h y ajustar exclusivamente cuando el hardware esté definido.
// config.h está ignorado por Git y no debe incluir credenciales reales.
#define WIFI_SSID "CHANGE_ME"
#define WIFI_PASSWORD "CHANGE_ME"
#define API_BASE_URL "http://192.168.1.10:8000"
#define DS18B20_PIN 4
#define SAMPLE_INTERVAL_MS 60000UL
#define MAX_FLUSH_PER_CYCLE 10
