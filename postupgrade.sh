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

# Refresh the central plugin metadata after restoring persistent configuration.
# This prevents an older backed-up plugin.cfg from surviving an update.
PTEMPPATH="${6:-}"
CFGDIR="$LBROOT/config/plugins/$PLUGIN_FOLDER"
if [ -n "$PTEMPPATH" ] && [ -f "$PTEMPPATH/plugin.cfg" ]; then
    mkdir -p "$CFGDIR"
    cp -f "$PTEMPPATH/plugin.cfg" "$CFGDIR/plugin.cfg"
    chown loxberry:loxberry "$CFGDIR/plugin.cfg" 2>/dev/null || true
    chmod 644 "$CFGDIR/plugin.cfg" 2>/dev/null || true
fi

# Fallback: restore the explicit config.json safety copy if the regular
# config-area restore did not produce a configuration file.
if [ ! -f "$LBROOT/config/plugins/$PLUGIN_FOLDER/config.json" ] && [ -f "$BACKUP/config.json" ]; then
    mkdir -p "$LBROOT/config/plugins/$PLUGIN_FOLDER"
    cp -a "$BACKUP/config.json" "$LBROOT/config/plugins/$PLUGIN_FOLDER/config.json"
fi

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

chmod +x "$LBROOT/bin/plugins/$PLUGIN_FOLDER/control_listener.py"          "$LBROOT/bin/plugins/$PLUGIN_FOLDER/control_watchdog.sh"          "$LBROOT/bin/plugins/$PLUGIN_FOLDER/control_cli.py" 2>/dev/null || true


# 1.0.1 migration: if UDP control was already enabled, initialize the allowed
# sender list from the Miniserver selected in the existing LoxBerry configuration.
# An empty explicit list remains fail-closed if no Miniserver can be resolved.
CFGFILE="$LBROOT/config/plugins/$PLUGIN_FOLDER/config.json"
BRIDGE="$LBROOT/bin/plugins/$PLUGIN_FOLDER/loxberry_bridge.pl"
if [ -f "$CFGFILE" ] && [ -x "$BRIDGE" ]; then
    MSJSON="$($BRIDGE list 2>/dev/null || true)"
    python3 - "$CFGFILE" "$MSJSON" <<'PYMIG' || true
import json,os,sys
p=sys.argv[1]
try:
    cfg=json.load(open(p,encoding="utf-8"))
    control=cfg.get("control") if isinstance(cfg.get("control"),dict) else {}
    if "allowed_senders" not in control:
        raw=json.loads(sys.argv[2] or "[]")
        if isinstance(raw,dict): raw=[raw]
        wanted=int(cfg.get("miniserver_no",1) or 1)
        ips=[]
        for i,ms in enumerate(raw if isinstance(raw,list) else [],1):
            if not isinstance(ms,dict): continue
            no=int(ms.get("_msno",i) or i)
            ip=str(ms.get("IPAddress") or ms.get("ipaddress") or ms.get("IP") or ms.get("ip") or "").strip()
            if no==wanted and ip: ips.append(ip)
        control["allowed_senders"]=sorted(set(ips))
        cfg["control"]=control
        tmp=p+".tmp"
        with open(tmp,"w",encoding="utf-8") as f: json.dump(cfg,f,indent=2,ensure_ascii=False)
        os.chmod(tmp,0o600); os.replace(tmp,p)
except Exception:
    pass
PYMIG
fi

# PID-Datei aus dem Backup darf nie weiterverwendet werden:
# der alte Listener-Prozess wurde vor dem Upgrade beendet.
rm -f "$LBROOT/data/plugins/$PLUGIN_FOLDER/control_listener.pid"

# Listener mit dem NEU installierten Code neu starten, falls UDP-Steuerung aktiviert ist.
"$LBROOT/bin/plugins/$PLUGIN_FOLDER/control_watchdog.sh" >/dev/null 2>&1 || true

exit 0
