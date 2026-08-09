#!/bin/bash
set -e
TMPID="$1"
PLUGIN_FOLDER="$3"
LBROOT="$5"
BACKUP="/tmp/${TMPID}_${PLUGIN_FOLDER}_upgrade"

# Alte Cron-Struktur aus fruehen Versionen vor dem Upgrade bereinigen.
CRONDIR="$LBROOT/system/cron/cron.01min"
if [ -d "$CRONDIR/velux_active_connect" ]; then
    rm -rf "$CRONDIR/velux_active_connect"
fi
rm -f "$CRONDIR/velux_active_connect" "$CRONDIR/veluxactive" 2>/dev/null || true
rm -rf "$BACKUP"
mkdir -p "$BACKUP"
for area in config data log; do
    SRC="$LBROOT/$area/plugins/$PLUGIN_FOLDER"
    if [ -d "$SRC" ]; then
        mkdir -p "$BACKUP/$area"
        cp -a "$SRC" "$BACKUP/$area/"
    fi
done
echo "VELUX Active Connect: Konfiguration und Plugin-Daten für Upgrade gesichert."
exit 0
