#!/bin/bash
# Fleet-wide one-line status for every pm2-managed miner process.
# Complements scripts/miner_healthcheck.sh (single process) with a roll-up of
# status, uptime, restarts, and the most recent scoring line per process.
# Usage: scripts/fleet_status.sh [name-filter]
set -euo pipefail
FILTER="${1:-}"

pm2 jlist | FILTER="$FILTER" python3 -c "
import json, os, sys, time

flt = os.environ.get('FILTER', '')
now = time.time() * 1000.0
procs = json.load(sys.stdin)
print(f\"{'name':<20} {'status':<9} {'uptime':>9} {'restarts':>8}\")
for p in procs:
    name = p.get('name', '?')
    if flt and flt not in name:
        continue
    env = p.get('pm2_env', {})
    status = env.get('status', '?')
    restarts = env.get('restart_time', 0)
    started = env.get('pm_uptime') or now
    up_s = max(0, (now - started) / 1000.0)
    if up_s >= 3600:
        up = f'{up_s/3600:.1f}h'
    elif up_s >= 60:
        up = f'{up_s/60:.1f}m'
    else:
        up = f'{up_s:.0f}s'
    print(f'{name:<20} {status:<9} {up:>9} {restarts:>8}')
"

# Tail the last scoring line per process so silence is visible at a glance.
for LOG in "$HOME"/.pm2/logs/*-out.log; do
  [ -f "$LOG" ] || continue
  base="$(basename "$LOG" -out.log)"
  if [ -n "$FILTER" ] && [[ "$base" != *"$FILTER"* ]]; then
    continue
  fi
  last="$(grep 'Scored' "$LOG" 2>/dev/null | tail -1 | sed -E 's/\x1b\[[0-9;]*m//g')"
  [ -n "$last" ] && echo "  $base: $last"
done
