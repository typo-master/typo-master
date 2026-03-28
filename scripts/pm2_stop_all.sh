#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

export PM2_HOME="${PM2_HOME:-$ROOT_DIR/.pm2}"
mkdir -p "$PM2_HOME"

listener_pids_for_port() {
  local port="$1"
  lsof -ti "tcp:$port" -sTCP:LISTEN || true
}

kill_port_listeners() {
  local port="$1"
  local pids pid
  pids="$(listener_pids_for_port "$port")"
  for pid in $pids; do
    kill -TERM "$pid" 2>/dev/null || true
  done
  sleep 1
  pids="$(listener_pids_for_port "$port")"
  for pid in $pids; do
    kill -KILL "$pid" 2>/dev/null || true
  done
}

for app in typomaster-backend typomaster-frontend; do
  pm2 delete "$app" >/dev/null 2>&1 || true
done

pm2 status || true

# Also clear listeners in case legacy or detached processes survived PM2 deletion.
kill_port_listeners 50120
kill_port_listeners 50121
kill_port_listeners 5173
