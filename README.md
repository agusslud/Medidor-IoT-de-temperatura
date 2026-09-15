# Farmacia Cold Chain Monitor

Sistema IoT para monitorear 24/7 la cadena de frío de vacunas y medicamentos
(2–8 °C). El proyecto separa el firmware de adquisición (ESP32) del servidor
local y las alarmas (Raspberry Pi), para que una caída de red no haga perder
mediciones.

## Estado

Base de proyecto inicial. Todavía no se asumieron pines, credenciales ni
topología eléctrica: esas decisiones se concentran en archivos de configuración
para evitar que queden embebidas en el código.

## Estructura

- `firmware/`: ESP32 con PlatformIO/Arduino.
- `server/`: API FastAPI, SQLite y tareas de alarma.
- `docs/`: contratos, arquitectura y decisiones de ingeniería.
- `infra/`: servicios systemd para la Raspberry Pi.
- `.github/`: CI y plantillas para el flujo de GitHub.

## Inicio rápido para desarrollo

Requiere Python 3.11+ para el servidor y PlatformIO Core para el firmware.

```bash
cp server/.env.example server/.env
python -m venv .venv
. .venv/bin/activate
pip install -e 'server[dev]'
uvicorn app.main:app --app-dir server --reload
pytest server/tests

cd firmware
pio run
```

La API queda disponible en `http://127.0.0.1:8000/docs`. No publicar
credenciales, tokens de Telegram ni archivos `.env`.

## Publicar en GitHub

Cuando el repositorio local esté inicializado y exista uno vacío en GitHub:

```bash
git remote add origin git@github.com:ORG_O_USUARIO/farmacia-cold-chain-monitor.git
git branch -M main
git add .
git commit -m "chore: initial project scaffold"
git push -u origin main
```

Ver [docs/architecture.md](docs/architecture.md) antes de fijar hardware o
ampliar el protocolo.
