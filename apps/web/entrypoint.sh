#!/bin/sh
set -e

# Generate env.js with runtime environment variables
# This allows configuration at container startup instead of build time

cat <<EOF > /usr/share/nginx/html/env.js
window.__ENV__ = {
  VITE_API_BASE_URL: "${VITE_API_BASE_URL:-/api}",
  VITE_BACKEND_URL: "${VITE_BACKEND_URL:-/api}",
  VITE_SERVER_MODE: "${VITE_SERVER_MODE:-false}",
  VITE_DEFAULT_MQTT_BROKER: "${VITE_DEFAULT_MQTT_BROKER:-}",
  VITE_DEFAULT_MQTT_PORT: "${VITE_DEFAULT_MQTT_PORT:-1883}",
  VITE_DEFAULT_TOPIC_PREFIX: "${VITE_DEFAULT_TOPIC_PREFIX:-myelectricaldata}",
  VITE_DEFAULT_ENTITY_PREFIX: "${VITE_DEFAULT_ENTITY_PREFIX:-myelectricaldata}",
  VITE_DEFAULT_DISCOVERY_PREFIX: "${VITE_DEFAULT_DISCOVERY_PREFIX:-homeassistant}",
  VITE_DEFAULT_HA_URL: "${VITE_DEFAULT_HA_URL:-}",
  VITE_DEFAULT_VM_URL: "${VITE_DEFAULT_VM_URL:-}",
};
EOF

# Make env.js readable by nginx
chmod 644 /usr/share/nginx/html/env.js

echo "Generated /usr/share/nginx/html/env.js with:"
cat /usr/share/nginx/html/env.js

# Start nginx
exec nginx -g "daemon off;"
