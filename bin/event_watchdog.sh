#!/bin/bash
PLUGIN=veluxactive; LBROOT="${LBHOMEDIR:-/opt/loxberry}"; CFG="$LBROOT/config/plugins/$PLUGIN/config.json"; DATA="$LBROOT/data/plugins/$PLUGIN"; BIN="$LBROOT/bin/plugins/$PLUGIN"; LOG="$LBROOT/log/plugins/$PLUGIN"; mkdir -p "$DATA" "$LOG"
enabled=$(python3 - "$CFG" <<'PY'
import json,sys
try:
 d=json.load(open(sys.argv[1])); print('1' if d.get('plugin_enabled',True) and (d.get('eventstream') or {}).get('enabled',False) else '0')
except: print('0')
PY
)
pidfile="$DATA/event_listener.pid"
if [ "$enabled" != "1" ]; then
 if [ -f "$pidfile" ]; then pid=$(cat "$pidfile" 2>/dev/null); [ -n "$pid" ] && kill "$pid" 2>/dev/null || true; rm -f "$pidfile"; fi; exit 0
fi
if [ -f "$pidfile" ]; then pid=$(cat "$pidfile" 2>/dev/null); if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then exit 0; fi; rm -f "$pidfile"; fi
LBPCONFIGDIR="$LBROOT/config/plugins/$PLUGIN" LBPDATADIR="$DATA" LBPLOGDIR="$LOG" nohup python3 "$BIN/event_listener.py" </dev/null >>"$LOG/event_listener.stderr.log" 2>&1 &
