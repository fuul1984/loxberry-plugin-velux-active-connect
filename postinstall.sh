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
chmod +x "$LBROOT/bin/plugins/$PLUGIN_FOLDER/worker.py" \
         "$LBROOT/bin/plugins/$PLUGIN_FOLDER/velux_api.py" \
         "$LBROOT/bin/plugins/$PLUGIN_FOLDER/webui.py" \
         "$LBROOT/bin/plugins/$PLUGIN_FOLDER/loxberry_bridge.pl" \
         "$LBROOT/bin/plugins/$PLUGIN_FOLDER/control_listener.py" \
         "$LBROOT/bin/plugins/$PLUGIN_FOLDER/control_watchdog.sh" \
         "$LBROOT/webfrontend/htmlauth/plugins/$PLUGIN_FOLDER/index.cgi" 2>/dev/null || true
# Plugin-Laufzeitverzeichnisse muessen fuer CGI/Cron schreibbar sein.
chown -R loxberry:loxberry "$CFG" "$DATA" "$LOG" 2>/dev/null || true
chmod 750 "$CFG" "$DATA" "$LOG" 2>/dev/null || true

# LoxBerry versions/UI views have used both the installation folder and the
# plugin NAME when resolving dashboard icons. The installer already puts the
# icons below the folder name; provide the NAME alias as well so the start
# page can always resolve them.
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

# Scheduler wird über die standardmässige LoxBerry-Datei cron/cron.01min installiert.

chmod +x "$LBROOT/bin/plugins/$PLUGIN_FOLDER/velux_scheduler.py" 2>/dev/null || true

# Dependency for signed VELUX gateway control
"$LBROOT/bin/plugins/$PLUGIN_FOLDER/install_dependencies.sh" "$@" || true
chmod +x "$LBROOT/bin/plugins/$PLUGIN_FOLDER/control_cli.py" 2>/dev/null || true

# Frische Neuinstallation: Hauptlog leeren.
# Bei Updates wird postupgrade.sh verwendet, deshalb bleibt das Log dort erhalten.
: > "$LOG/veluxactive.log"
chown loxberry:loxberry "$LOG/veluxactive.log" 2>/dev/null || true
chmod 644 "$LOG/veluxactive.log" 2>/dev/null || true

# UDP-Control-Listener nach Neuinstallation starten, falls aktiviert.
rm -f "$DATA/control_listener.pid"
"$LBROOT/bin/plugins/$PLUGIN_FOLDER/control_watchdog.sh" >/dev/null 2>&1 || true

exit 0
