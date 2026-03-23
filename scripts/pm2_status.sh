#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

export PM2_HOME="${PM2_HOME:-$ROOT_DIR/.pm2}"
mkdir -p "$PM2_HOME"

pm2 status || true

echo "--- listeners ---"
lsof -nP -iTCP:50120 -sTCP:LISTEN || true
lsof -nP -iTCP:50121 -sTCP:LISTEN || true
lsof -nP -iTCP:5173 -sTCP:LISTEN || true

echo "--- probes ---"
curl -sS -i http://127.0.0.1:50120/api/v1/health | sed -n '1,10p' || true
curl -sS -i http://127.0.0.1:50121/ | sed -n '1,10p' || true
