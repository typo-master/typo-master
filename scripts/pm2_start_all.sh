#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

export PM2_HOME="${PM2_HOME:-$ROOT_DIR/.pm2}"
mkdir -p "$PM2_HOME"

# 创建日志目录
mkdir -p "$PM2_HOME/logs"

BACKEND_NAME="typemaster-backend"
FRONTEND_NAME="typemaster-frontend"
BACKEND_PORT=50120
FRONTEND_PORT=50121
LEGACY_FRONTEND_PORT=5173
BACKEND_HEALTH_URL="http://127.0.0.1:${BACKEND_PORT}/api/v1/health"
FRONTEND_URL="http://127.0.0.1:${FRONTEND_PORT}"

reset_stale_pm2_runtime() {
  local daemon_pid=""
  if [[ -f "$PM2_HOME/pm2.pid" ]]; then
    daemon_pid="$(tr -dc '0-9' < "$PM2_HOME/pm2.pid" || true)"
  fi

  if [[ -n "$daemon_pid" ]]; then
    kill -TERM "$daemon_pid" 2>/dev/null || true
    sleep 1
    if kill -0 "$daemon_pid" 2>/dev/null; then
      kill -KILL "$daemon_pid" 2>/dev/null || true
      sleep 1
    fi
  fi

  rm -f "$PM2_HOME/rpc.sock" "$PM2_HOME/pub.sock" "$PM2_HOME/pm2.pid"
}

get_pm2_pid() {
  local app_name="$1"
  pm2 pid "$app_name" 2>/dev/null | grep -E '^[0-9]+$' | head -n 1 || true
}

is_pm2_online() {
  local app_name="$1"
  local pid
  pid="$(get_pm2_pid "$app_name")"
  [[ -n "${pid}" && "${pid}" != "0" ]]
}

is_descendant_of() {
  local child_pid="$1"
  local ancestor_pid="$2"

  while [[ -n "$child_pid" && "$child_pid" != "1" ]]; do
    if [[ "$child_pid" == "$ancestor_pid" ]]; then
      return 0
    fi
    child_pid="$(ps -o ppid= -p "$child_pid" | tr -d '[:space:]' || true)"
  done
  return 1
}

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

validate_port_owner() {
  local app_name="$1"
  local port="$2"

  local app_pid listener_pids listener_pid
  app_pid="$(get_pm2_pid "$app_name")"

  if [[ -z "${app_pid}" || "${app_pid}" == "0" ]]; then
    echo "[warn] pm2 app pid missing for ${app_name}"
    return 1
  fi

  for _ in 1 2 3 4 5; do
    listener_pids="$(listener_pids_for_port "$port")"
    if [[ -n "${listener_pids}" ]]; then
      for listener_pid in $listener_pids; do
        if [[ "${listener_pid}" == "${app_pid}" ]] || is_descendant_of "${listener_pid}" "${app_pid}"; then
          return 0
        fi
      done
      echo "[warn] listeners on ${port} are not owned by ${app_name} (pm2 pid=${app_pid}): ${listener_pids}"
      return 1
    fi
    sleep 1
  done

  echo "[warn] no listener found on port ${port} for ${app_name}"
  return 1
}

http_ok() {
  local url="$1"
  local code
  code="$(curl -sS -o /dev/null -w "%{http_code}" "$url" || true)"
  [[ "$code" =~ ^2[0-9][0-9]$ || "$code" =~ ^3[0-9][0-9]$ ]]
}

# Clean same-name instances and known accidental names from earlier startup attempts.
# Recover from stale PM2 runtime socket state before issuing lifecycle commands.
if ! pm2 ping >/dev/null 2>&1; then
  echo "[warn] pm2 ping failed, resetting stale PM2 runtime state"
  reset_stale_pm2_runtime
fi
pm2 ping >/dev/null 2>&1 || true

pm2 delete "$BACKEND_NAME" >/dev/null 2>&1 || true
pm2 delete "$FRONTEND_NAME" >/dev/null 2>&1 || true
pm2 delete python3 >/dev/null 2>&1 || true
pm2 delete npm >/dev/null 2>&1 || true

# Keep selected project ports stable and reclaim them if occupied.
kill_port_listeners "$BACKEND_PORT"
kill_port_listeners "$FRONTEND_PORT"
if [[ "$LEGACY_FRONTEND_PORT" != "$FRONTEND_PORT" ]]; then
  kill_port_listeners "$LEGACY_FRONTEND_PORT"
fi

# 使用 ecosystem.config.js 启动服务（更好的保活配置）
pm2 start "$ROOT_DIR/ecosystem.config.js"

max_retries=5
attempt=1
while (( attempt <= max_retries )); do
  sleep 1

  backend_online=false
  frontend_online=false
  backend_port_ok=false
  frontend_port_ok=false
  backend_http_ok=false
  frontend_http_ok=false

  if is_pm2_online "$BACKEND_NAME"; then backend_online=true; fi
  if is_pm2_online "$FRONTEND_NAME"; then frontend_online=true; fi
  if validate_port_owner "$BACKEND_NAME" "$BACKEND_PORT"; then backend_port_ok=true; fi
  if validate_port_owner "$FRONTEND_NAME" "$FRONTEND_PORT"; then frontend_port_ok=true; fi
  if http_ok "$BACKEND_HEALTH_URL"; then backend_http_ok=true; fi
  if http_ok "$FRONTEND_URL"; then frontend_http_ok=true; fi

  if [[ "$backend_online" == true && "$frontend_online" == true && "$backend_port_ok" == true && "$frontend_port_ok" == true && "$backend_http_ok" == true && "$frontend_http_ok" == true ]]; then
    break
  fi

  echo "[retry ${attempt}/${max_retries}] startup validation failed"
  pm2 status
  pm2 logs "$BACKEND_NAME" --lines 20 --nostream || true
  pm2 logs "$FRONTEND_NAME" --lines 20 --nostream || true

  # Restart only when process status/HTTP probe is bad; keep noisy restarts away from reload transitions.
  if [[ "$backend_online" != true || "$backend_http_ok" != true ]]; then
    pm2 restart "$BACKEND_NAME" --update-env || true
  fi
  if [[ "$frontend_online" != true || "$frontend_http_ok" != true ]]; then
    pm2 restart "$FRONTEND_NAME" --update-env || true
  fi

  ((attempt++))
done

if (( attempt > max_retries )); then
  echo "[error] startup failed after retries"
  pm2 status
  exit 1
fi

# 保存 PM2 进程列表
pm2 save

echo "service_url=$FRONTEND_URL"
echo "frontend_url=$FRONTEND_URL"
echo "health_url=$BACKEND_HEALTH_URL"
echo "api_base_url=http://127.0.0.1:${BACKEND_PORT}/api/v1"
echo "${BACKEND_NAME}_url=http://127.0.0.1:${BACKEND_PORT}"
echo "${FRONTEND_NAME}_url=$FRONTEND_URL"
pm2 status
