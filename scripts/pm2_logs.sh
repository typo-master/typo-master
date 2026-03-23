#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

export PM2_HOME="${PM2_HOME:-$ROOT_DIR/.pm2}"
mkdir -p "$PM2_HOME"

pm2 logs typemaster-backend typemaster-frontend --lines "${1:-100}"
