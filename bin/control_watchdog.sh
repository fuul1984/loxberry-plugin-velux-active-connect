#!/bin/bash
PLUGIN=veluxactive
LBROOT="${LBHOMEDIR:-/opt/loxberry}"
CFG="$LBROOT/config/plugins/$PLUGIN/config.json"
DATA="$LBROOT/data/plugins/$PLUGIN"
BIN="$LBROOT/bin/plugins/$PLUGIN"
LOG="$LBROOT/log/plugins/$PLUGIN"
mkdir -p "$DATA" "$LOG"
enabled=$(python3 - "$CFG" <<'PY'
import json,sys
try:
 d=json.load(open(sys.argv[1])); print("1" if (d.get("control") or {}).get("enabled") else "0")
except Exception: print("0")
PY
)
pidfile="$DATA/control_listener.pid"
if [ "$enabled" != "1" ]; then
  if [ -f "$pidfile" ]; then pid=$(cat "$pidfile" 2>/dev/null); [ -n "$pid" ] && kill "$pid" 2>/dev/null || true; rm -f "$pidfile"; fi
  exit 0
fi
if [ -f "$pidfile" ]; then
  pid=$(cat "$pidfile" 2>/dev/null)
  if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then exit 0; fi
  rm -f "$pidfile"
fi
LBPCONFIGDIR="$LBROOT/config/plugins/$PLUGIN" LBPDATADIR="$DATA" LBPLOGDIR="$LOG" \
  nohup python3 "$BIN/control_listener.py" </dev/null >>"$LOG/control_listener.stderr.log" 2>&1 &
exit 0
