#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PM2_HOME="${PM2_HOME:-$ROOT_DIR/.pm2}"

# Check if services are already running
backend_running=false
frontend_running=false

if pm2 list | grep -q "typomaster-backend.*online"; then
    backend_running=true
fi

if pm2 list | grep -q "typomaster-frontend.*online"; then
    frontend_running=true
fi

# Start services only if not already running
if [[ "$backend_running" != "true" || "$frontend_running" != "true" ]]; then
    echo "Starting services..."
    pm2 start "$ROOT_DIR/ecosystem.config.js"
    sleep 20
fi

# Check health and restart only if needed
if ! curl -sf http://127.0.0.1:50120/api/v1/health > /dev/null 2>&1; then
    echo "Backend health check failed, restarting..."
    pm2 restart typomaster-backend
    sleep 15
fi

if ! curl -sf http://127.0.0.1:50121 > /dev/null 2>&1; then
    echo "Frontend health check failed, restarting..."
    pm2 restart typomaster-frontend
    sleep 10
fi

# Save process list
pm2 save

# Display status
pm2 status

echo ""
echo "=== Service URLs ==="
echo "Frontend: http://127.0.0.1:50121"
echo "Backend:  http://127.0.0.1:50120"
echo "API Health: http://127.0.0.1:50120/api/v1/health"
