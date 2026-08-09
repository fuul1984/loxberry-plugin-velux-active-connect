#!/bin/bash
LBROOT="${5:-${LBHOMEDIR:-/opt/loxberry}}"
DATA="$LBROOT/data/plugins/veluxactive"
if [ -f "$DATA/control_listener.pid" ]; then
  pid=$(cat "$DATA/control_listener.pid" 2>/dev/null)
  [ -n "$pid" ] && kill "$pid" 2>/dev/null || true
  rm -f "$DATA/control_listener.pid"
fi
rm -rf "$LBROOT/system/cron/cron.01min/velux_active_connect" "$LBROOT/system/cron/cron.01min/veluxactive" 2>/dev/null || true
exit 0
