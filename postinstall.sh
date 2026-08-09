#!/bin/bash
set -e
PLUGIN_FOLDER="${3:-veluxactive}"
LBROOT="${5:-${LBHOMEDIR:-/opt/loxberry}}"
CFG="$LBROOT/config/plugins/$PLUGIN_FOLDER"
DATA="$LBROOT/data/plugins/$PLUGIN_FOLDER"
LOG="$LBROOT/log/plugins/$PLUGIN_FOLDER"
TEMPLATE="$LBROOT/templates/plugins/$PLUGIN_FOLDER/default.json"

mkdir -p "$CFG" "$DATA" "$LOG"
if [ ! -f "$CFG/config.json" ]; then
    if [ -f "$TEMPLATE" ]; then
        cp "$TEMPLATE" "$CFG/config.json"
    else
        echo "Default-Konfiguration fehlt: $TEMPLATE" >&2
        exit 1
    fi
fi
chmod 600 "$CFG/config.json" || true

chmod +x \
  "$LBROOT/bin/plugins/$PLUGIN_FOLDER/worker.py" \
  "$LBROOT/bin/plugins/$PLUGIN_FOLDER/velux_api.py" \
  "$LBROOT/bin/plugins/$PLUGIN_FOLDER/webui.py" \
  "$LBROOT/bin/plugins/$PLUGIN_FOLDER/loxberry_bridge.pl" \
  "$LBROOT/bin/plugins/$PLUGIN_FOLDER/control_listener.py" \
  "$LBROOT/bin/plugins/$PLUGIN_FOLDER/control_cli.py" \
  "$LBROOT/bin/plugins/$PLUGIN_FOLDER/control_watchdog.sh" \
  "$LBROOT/bin/plugins/$PLUGIN_FOLDER/gateway_pair.py" \
  "$LBROOT/bin/plugins/$PLUGIN_FOLDER/pairing.py" \
  "$LBROOT/bin/plugins/$PLUGIN_FOLDER/signing.py" \
  "$LBROOT/bin/plugins/$PLUGIN_FOLDER/install_dependencies.sh" \
  "$LBROOT/webfrontend/htmlauth/plugins/$PLUGIN_FOLDER/index.cgi" 2>/dev/null || true

chown -R loxberry:loxberry "$CFG" "$DATA" "$LOG" 2>/dev/null || true
chmod 750 "$CFG" "$DATA" "$LOG" 2>/dev/null || true

ICON_BASE="$LBROOT/webfrontend/html/system/images/icons"
ICON_SRC="$ICON_BASE/$PLUGIN_FOLDER"
ICON_ALIAS="$ICON_BASE/velux_active_connect"
if [ -d "$ICON_SRC" ]; then
    mkdir -p "$ICON_ALIAS"
    cp -f "$ICON_SRC"/icon_*.png "$ICON_ALIAS"/ 2>/dev/null || true
    chown -R loxberry:loxberry "$ICON_SRC" "$ICON_ALIAS" 2>/dev/null || true
    chmod 755 "$ICON_SRC" "$ICON_ALIAS" 2>/dev/null || true
    chmod 644 "$ICON_SRC"/icon_*.png "$ICON_ALIAS"/icon_*.png 2>/dev/null || true
fi

CRONDIR="$LBROOT/system/cron/cron.01min"
mkdir -p "$CRONDIR"
rm -rf "$CRONDIR/velux_active_connect" "$CRONDIR/veluxactive" 2>/dev/null || true
cat > "$CRONDIR/veluxactive" <<EOF
#!/bin/bash
python3 "$LBROOT/bin/plugins/$PLUGIN_FOLDER/worker.py" >/dev/null 2>&1
"$LBROOT/bin/plugins/$PLUGIN_FOLDER/control_watchdog.sh" >/dev/null 2>&1
EOF
chmod 755 "$CRONDIR/veluxactive"
chown loxberry:loxberry "$CRONDIR/veluxactive" 2>/dev/null || true

"$LBROOT/bin/plugins/$PLUGIN_FOLDER/install_dependencies.sh" "$@" || true
exit 0
