# Contrato experimental v2 y simulación

Este contrato es independiente de `POST /api/telemetry`: no se ha añadido un endpoint,
no se ha cambiado la base de datos ni se ha conectado al firmware. Los modelos
ejecutables están en `server/app/contract_v2.py` y la simulación en
`server/app/contract_simulation.py`. No es apto para uso sanitario real.

Cada mensaje incluye `schema_version: 2`, `type`, `device_id`, un `boot_id` UUID
único por arranque y `uptime_ms` monotónico de 64 bits desde ese arranque. El tiempo
se envía en UTC con `Z` o `+00:00`. Los resúmenes y eventos incluyen `sequence`,
`observed_at` y `time_quality` (`synchronized`, `estimated`, `unknown`). Si la hora
es desconocida se envía `observed_at: null`. La fecha de recepción pertenece al
servidor y no sustituye la fecha de medición.

## Mensajes

Cada diez minutos se emite un resumen. El instante es el final de la ventana;
temperaturas son lecturas calibradas y `valid_samples` cuenta muestras válidas.
Si no hay ninguna, las tres temperaturas son `null`; una falla de sensor no debe
interpretarse como una temperatura fuera de rango.

```json
{"schema_version":2,"type":"temperature_summary","device_id":"ESP32_FARMACIA_01",
 "boot_id":"d1a678a8-693b-4ec2-9210-f4536743de35","sequence":1,"uptime_ms":600000,
 "observed_at":"2026-10-26T15:10:00Z","time_quality":"synchronized",
 "temperature_last_c":4.2,"temperature_min_c":3.8,"temperature_max_c":4.7,
 "valid_samples":10,"sensor_status":"OK","power_source":"MAIN_POWER"}
```

Un evento se emite inmediatamente al cambiar estado de sensor, temperatura o fuente;
`records_lost` informa la cantidad acumulada de registros reemplazados.

```json
{"schema_version":2,"type":"event","device_id":"ESP32_FARMACIA_01",
 "boot_id":"d1a678a8-693b-4ec2-9210-f4536743de35","sequence":2,"uptime_ms":720000,
 "observed_at":null,"time_quality":"unknown","event_type":"sensor_fault",
 "temperature_c":null,"power_source":"BATTERY","lost_count":null}
```

El heartbeat se envía cada minuto cuando hay conexión, sin ocupar la cola histórica:

```json
{"schema_version":2,"type":"heartbeat","device_id":"ESP32_FARMACIA_01",
 "boot_id":"d1a678a8-693b-4ec2-9210-f4536743de35","uptime_ms":780000,
 "buffered_records":2,"sensor_status":"FAULT","power_source":"BATTERY"}
```

La respuesta del heartbeat contiene `server_time` UTC y `time_quality` igual a
`synchronized` o `unknown`; si el servidor no tiene hora confiable, usa `null`.

## Entrega y tiempo

La clave `(device_id, boot_id, sequence)` identifica un registro. La simulación
responde `stored` para inserción nueva, `duplicate` para contenido idéntico y
`conflict` para la misma clave con contenido diferente. Solo `stored` y `duplicate`
permiten retirar un registro después de recibir la confirmación. Si se pierde la
confirmación se reintenta; el conflicto queda pendiente para diagnóstico.

La cola simulada reserva 144 posiciones para resúmenes de 24 horas y 16 para eventos.
Un exceso de eventos reemplaza únicamente los eventos más antiguos y no desplaza
los resúmenes. Cuando se llena cada sección, reemplaza su registro más antiguo e
incrementa un contador acumulativo. El aviso de pérdida se encola cuando haya
espacio; si continúan pérdidas, se comunica un nuevo valor acumulado. No se borra
el contador en la simulación. El diseño físico y la durabilidad requieren pruebas.

Solo se estima una hora con un ancla UTC confiable del mismo arranque y posterior
al registro. Si falta ancla o hay un reinicio, se conserva `unknown`: nunca se
generan mediciones durante un apagado. Los detalles de incertidumbre y resincronización
del reloj deberán definirse antes de implementar el sistema real.
