# Arquitectura y decisiones iniciales

## Límites de responsabilidad

| Capa | Responsabilidad | No debe hacer |
| --- | --- | --- |
| ESP32 | Medir, validar sensor, aplicar calibración, persistir cola offline y entregar telemetría | Decidir alarmas clínicas ni depender de Internet |
| Raspberry Pi | Recibir, persistir, detectar alarmas, notificar y presentar datos | Confiar en una temperatura inválida |
| UI | Consultar historial y mostrar estado | Ser fuente de verdad |

## Flujo de telemetría

1. El ESP32 toma una lectura cada 60 s y aplica el `offset` guardado en NVS.
2. Publica `POST /api/telemetry` por la LAN. Un 200/201 confirma entrega.
3. Ante fallo de Wi-Fi/API, encola el registro localmente. Al volver la conexión,
   reintenta en lotes limitados y en orden.
4. El servidor registra datos, evalúa alarma de temperatura, fallo de sensor y
   ausencia de heartbeat.

## Decisiones que faltan antes de producción

- Pines del ESP32, resistencia pull-up y alimentación final de la sonda.
- Política de retención de SQLite y capacidad mínima del buffer offline.
- Identidad/autenticación mutua de cada dispositivo; HTTP sin autenticación solo
  es admisible para desarrollo en red aislada.
- Fuente de tiempo: NTP con estado explícito o contador de secuencia mientras
  no haya reloj válido.

La especificación de API está en [telemetry-contract.md](telemetry-contract.md).
