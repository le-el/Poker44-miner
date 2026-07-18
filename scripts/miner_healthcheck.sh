#!/bin/bash
# Quick health snapshot for a running Poker44 miner under pm2.
# Usage: scripts/miner_healthcheck.sh <pm2-process-name>
set -euo pipefail
NAME="${1:?usage: miner_healthcheck.sh <pm2-name>}"
pm2 describe "$NAME" | grep -E "status|uptime|restarts" || true
LOG="$HOME/.pm2/logs/${NAME//_/-}-out.log"
if [ -f "$LOG" ]; then
  echo "--- recent scoring activity ---"
  grep "Scored" "$LOG" | tail -3
  echo "--- last errors (if any) ---"
  tail -5 "${LOG/-out/-error}" 2>/dev/null || true
fi
