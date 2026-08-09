#!/bin/bash
set -e
TMPID="$1"
PLUGIN_FOLDER="$3"
LBROOT="$5"
BACKUP="/tmp/${TMPID}_${PLUGIN_FOLDER}_upgrade"
for area in config data log; do
    SRC="$BACKUP/$area/$PLUGIN_FOLDER"
    DEST="$LBROOT/$area/plugins/$PLUGIN_FOLDER"
    if [ -d "$SRC" ]; then
        mkdir -p "$LBROOT/$area/plugins"
        rm -rf "$DEST"
        cp -a "$SRC" "$DEST"
    fi
done
rm -rf "$BACKUP"
# Make sure new files remain executable after restoring persistent areas.
chmod +x "$LBROOT/webfrontend/htmlauth/plugins/$PLUGIN_FOLDER/index.cgi" \
         "$LBROOT/bin/plugins/$PLUGIN_FOLDER/worker.py" \
         "$LBROOT/bin/plugins/$PLUGIN_FOLDER/velux_api.py" \
         "$LBROOT/bin/plugins/$PLUGIN_FOLDER/webui.py" \
         "$LBROOT/bin/plugins/$PLUGIN_FOLDER/loxberry_bridge.pl" 2>/dev/null || true
echo "VELUX Active Connect: bestehende Konfiguration und Plugin-Daten wiederhergestellt."
chown -R loxberry:loxberry "$LBROOT/config/plugins/$PLUGIN_FOLDER" "$LBROOT/data/plugins/$PLUGIN_FOLDER" "$LBROOT/log/plugins/$PLUGIN_FOLDER" 2>/dev/null || true
# Keep dashboard icon resolution compatible with both folder and plugin name.
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
exit 0

chmod +x "$LBROOT/bin/plugins/$PLUGIN_FOLDER/control_listener.py" "$LBROOT/bin/plugins/$PLUGIN_FOLDER/control_watchdog.sh" 2>/dev/null || true

chmod +x "$LBROOT/bin/plugins/$PLUGIN_FOLDER/control_cli.py" 2>/dev/null || true
