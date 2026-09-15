# Contrato de telemetría v1

`POST /api/telemetry` recibe un objeto JSON. La versión inicial evita timestamps
originados por el ESP32; el servidor asigna el instante de recepción. Cuando se
incorpore NTP, se agregará `measured_at` en una versión compatible del contrato.

```json
{
  "device_id": "ESP32_FARMACIA_01",
  "temperature": 4.25,
  "raw_temperature": 4.05,
  "offset_applied": 0.20,
  "sensor_status": "OK",
  "power_source": "MAIN_POWER",
  "buffered_records": 0
}
```

Valores permitidos: `sensor_status` es `OK` o `FAULT`; `power_source` es
`MAIN_POWER`, `BATTERY` o `UNKNOWN`. Las lecturas `FAULT` no se usan para
determinar el rango térmico.
