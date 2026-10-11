#!/bin/bash
# Crea el usuario MQTT de la plataforma (agrohub-plataforma): el que usa este backend para leer la
# configuración vigente de los gateways, cambiarla (config/set) y mandar órdenes de válvula
# (control/valvulas). NO puede publicar cloud/health: con ese latido el gateway deja de decidir el
# riego solo, y por ahora la plataforma solo configura umbrales y manda órdenes manuales.
#
# Correr UNA vez, en el servidor, con sudo:   sudo ./scripts/crear_usuario_mqtt_plataforma.sh
# Si el usuario ya existe, mosquitto_passwd solo le cambia la contraseña (hay que actualizar el .env).
set -euo pipefail

PASSWD_FILE="/etc/mosquitto/passwd"
ACL_FILE="/etc/mosquitto/acl.conf"
USUARIO="agrohub-plataforma"
PASSWORD=$(openssl rand -hex 16)

mosquitto_passwd -b "$PASSWD_FILE" "$USUARIO" "$PASSWORD"

if ! grep -q "^user ${USUARIO}$" "$ACL_FILE" 2>/dev/null; then
    cat >> "$ACL_FILE" << EOF2

# --- ${USUARIO} (backend agrohub: configuración remota y órdenes de válvula) ---
user ${USUARIO}
topic read  ahub/+/config/state
topic read  ahub/+/valvulas/state
topic read  ahub/+/health
topic read  ahub/+/status
topic write ahub/+/config/set
topic write ahub/+/control/valvulas
EOF2
fi

systemctl reload mosquitto

cat << EOF3

Usuario creado.

  Usuario:  ${USUARIO}
  Password: ${PASSWORD}

Agrega al .env del backend (/home/hubambiental002/backend_stacks/agrohub_backend/.env):

  RIEGO_IOT_MQTT_USER=${USUARIO}
  RIEGO_IOT_MQTT_PASSWORD=${PASSWORD}

(host 127.0.0.1 y puerto 1883 son los valores por defecto: el listener local del broker, sin TLS)
y reinicia:  sudo systemctl restart agrohub-backend

Guarda la contraseña ahora: mosquitto_passwd solo guarda el hash.
EOF3
