# Despliegue inicial en Raspberry Pi

1. Crear un usuario de servicio sin privilegios: `sudo useradd --system --create-home farmacia`.
2. Clonar este repositorio en `/opt/farmacia-cold-chain-monitor` y crear el entorno virtual.
3. Copiar `server/.env.example` a `/etc/farmacia-monitor.env`, completar valores y restringirlo:
   `sudo chmod 600 /etc/farmacia-monitor.env`.
4. Instalar las unidades de `infra/systemd/`, ejecutar `sudo systemctl daemon-reload` y habilitar
   `farmacia-monitoreo.service` y `farmacia-heartbeat.timer`.

No se incluye todavía una tarea que actualice paquetes automáticamente. Para un equipo de
cadena de frío, las actualizaciones deben probarse y aprobarse antes de llegar a producción;
una actualización desatendida puede dejar el monitor inoperativo en el peor momento.
