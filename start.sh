#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PM2_HOME="${PM2_HOME:-$ROOT_DIR/.pm2}"

"$ROOT_DIR/scripts/pm2_start_all.sh"
