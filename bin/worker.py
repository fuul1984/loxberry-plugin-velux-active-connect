#!/usr/bin/env python3
from __future__ import annotations
import json, os, re, subprocess, sys, time, traceback
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

PLUGIN="veluxactive"
CFG=Path(os.environ.get("LBPCONFIGDIR") or os.environ.get("LBPCONFIG") or f"/opt/loxberry/config/plugins/{PLUGIN}")
LOG=Path(os.environ.get("LBPLOGDIR") or os.environ.get("LBPLOG") or f"/opt/loxberry/log/plugins/{PLUGIN}")
DATA=Path(os.environ.get("LBPDATADIR") or os.environ.get("LBPDATA") or f"/opt/loxberry/data/plugins/{PLUGIN}")
for p in (CFG,LOG,DATA): p.mkdir(parents=True, exist_ok=True)
CONFIG=CFG/"config.json"; TOKENS=CFG/"tokens.json"; STATE=DATA/"state.json"; RUN=DATA/"last_run.json"; UDP_LAST=DATA/"udp_last_sent.json"
RAW_HOMES=DATA/"raw_homesdata.json"; RAW_STATUS=DATA/"raw_homestatus.json"; LOGFILE=LOG/"veluxactive.log"

def log(msg):
    line=time.strftime("%Y-%m-%d %H:%M:%S ")+str(msg)+"\n"
    try:
        LOG.mkdir(parents=True, exist_ok=True)
        with LOGFILE.open("a",encoding="utf-8") as f:
            f.write(line)
        return True
    except Exception:
        try:
            sys.stderr.write("LOGGING FEHLER: "+line)
        except Exception:
            pass
        return False

def load(path, default):
    try: return json.loads(path.read_text(encoding="utf-8"))
    except Exception: return default

def save(path,obj,mode=0o600):
    tmp=path.with_suffix(path.suffix+".tmp")
    tmp.write_text(json.dumps(obj,indent=2,ensure_ascii=False), encoding="utf-8")
    os.chmod(tmp,mode); tmp.replace(path)

def slug(s):
    text=str(s).strip().translate(str.maketrans({"ä":"ae","ö":"oe","ü":"ue","Ä":"Ae","Ö":"Oe","Ü":"Ue","ß":"ss"}))
    return re.sub(r"[^a-zA-Z0-9_]+","_",text).strip("_").lower() or "unknown"

def ensure_token(cfg, force_login=False):
    tok=load(TOKENS,{})
    if force_login:
        tok={}
    if tok.get("access_token") and int(tok.get("expires_at",0)) > time.time()+120:
        return tok, "cached"
    if tok.get("refresh_token"):
        try:
            new=refresh(tok["refresh_token"]); new.setdefault("refresh_token",tok["refresh_token"]); save(TOKENS,new)
            return new, "refreshed"
        except Exception as e:
            log("Token refresh fehlgeschlagen: "+str(e))
    new=login(cfg.get("email",""),cfg.get("password","")); save(TOKENS,new)
    return new, "login"

def extract_homes(raw):
    return ((raw.get("body") or {}).get("homes") or [])

def flatten(raw, status_by_home):
    result={"homes":[],"rooms":[],"devices":[],"values":{},"value_meta":{}}
    homes=extract_homes(raw)

    def normalize_value(key, value, unit=""):
        # VELUX climate values can arrive as tenths of a degree (267 -> 26.7 °C).
        # Normalize every value explicitly marked as Celsius, independent of where
        # it came from, so Status, UDP and logging all use the same value.
        if unit == "°C" or key in {"temperature", "min_comfort_temperature", "max_comfort_temperature", "therm_measured_temperature"}:
            try:
                number=float(value)
            except (TypeError, ValueError):
                return value
            if abs(number) > 80:
                number /= 10.0
            return round(number, 1)
        if isinstance(value, bool):
            return 1 if value else 0
        return value

    def add_value(key, value, label, unit="", category="", source=""):
        if value is None:
            return
        value=normalize_value(key.split(".")[-1], value, unit)
        result["values"][key]=value
        result["value_meta"][key]={
            "label":label,
            "unit":unit,
            "category":category,
            "source":source,
        }

    for topo_home in homes:
        hid=topo_home.get("id",""); hname=topo_home.get("name",hid)
        status_home=((status_by_home.get(hid,{ }).get("body") or {}).get("home") or {})
        topo_rooms={r.get("id"):r for r in topo_home.get("rooms",[]) or [] if r.get("id")}
        status_rooms={r.get("id"):r for r in status_home.get("rooms",[]) or [] if r.get("id")}
        rooms=[]
        for rid in sorted(set(topo_rooms)|set(status_rooms)):
            r=dict(topo_rooms.get(rid,{})); r.update(status_rooms.get(rid,{})); rooms.append(r)
        topo_mods={m.get("id"):m for m in topo_home.get("modules",[]) or [] if m.get("id")}
        status_mods={m.get("id"):m for m in status_home.get("modules",[]) or [] if m.get("id")}
        modules=[]
        for mid in sorted(set(topo_mods)|set(status_mods)):
            m=dict(topo_mods.get(mid,{})); m.update(status_mods.get(mid,{})); modules.append(m)

        room_name_by_id={r.get("id",""): (r.get("name") or r.get("id") or "Raum") for r in rooms}
        # Some API payloads associate modules via room.module_ids rather than module.room_id.
        module_room_by_id={}
        for r in rooms:
            rid=r.get("id","")
            for mid in (r.get("module_ids") or []):
                module_room_by_id[mid]=rid

        result["homes"].append({"id":hid,"name":hname,"room_count":len(rooms),"module_count":len(modules)})
        for room in rooms:
            rid=room.get("id",""); rlabel=room.get("name",rid or "Raum"); rname=slug(rlabel)
            result["rooms"].append({"id":rid,"name":rlabel,"home_id":hid})
            room_values = (
                ("temperature", "Temperatur", "°C", "Klima"),
                ("therm_measured_temperature", "Gemessene Temperatur", "°C", "Klima"),
                ("min_comfort_temperature", "Komforttemperatur min.", "°C", "Klima"),
                ("max_comfort_temperature", "Komforttemperatur max.", "°C", "Klima"),
                ("humidity", "Luftfeuchtigkeit", "%", "Klima"),
                ("co2", "CO₂", "ppm", "Klima"),
                ("lux", "Helligkeit", "lx", "Klima"),
                ("air_quality", "Luftqualität", "", "Klima"),
                ("algo_status", "Automatikstatus", "", "Status"),
                ("auto_close_ts", "Auto-Close Zeitpunkt", "", "Status"),
            )
            for key,label,unit,category in room_values:
                if room.get(key) is not None:
                    add_value(f"room.{rname}.{key}", room[key], f"{rlabel} – {label}", unit, category, rlabel)

        used_slugs={}
        for module in modules:
            mid=module.get("id",""); mlabel=module.get("module_name") or module.get("name") or mid or "Gerät"
            base_slug=slug(mlabel)
            used_slugs[base_slug]=used_slugs.get(base_slug,0)+1
            mname=base_slug if used_slugs[base_slug]==1 else f"{base_slug}_{slug(mid)[-6:]}"
            dtype=module.get("type","")
            rid=module.get("room_id") or module_room_by_id.get(mid,"")
            room_label=room_name_by_id.get(rid,"")
            position=next((module.get(k) for k in ("current_position","target_position","position") if module.get(k) is not None), None)
            role="Aktor" if position is not None else "Sensor / Gateway"
            device={
                "id":mid,"name":mlabel,"type":dtype,"home_id":hid,"bridge":module.get("bridge",""),
                "room_id":rid,"room_name":room_label,"udp_key":mname,"role":role,
            }
            for key in ("reachable","battery_percent","battery_level","battery_state","rf_strength","rf_state","last_seen","firmware","firmware_revision","current_position","target_position","position","mode","is_raining","rain","rain_detected","raining"):
                if module.get(key) is not None:
                    device[key]=module[key]
            # Rain status is exposed as `is_raining` by the current VELUX/pyatmo
            # implementation. Accept a few raw aliases as well and dashboard_data
            # for forward/backward compatibility with VELUX payload changes.
            dashboard=module.get("dashboard_data") if isinstance(module.get("dashboard_data"),dict) else {}
            rain_value=None
            rain_source=""
            for rk in ("is_raining","rain_detected","raining","rain"):
                if module.get(rk) is not None:
                    rain_value=module.get(rk); rain_source=rk; break
                if dashboard.get(rk) is not None:
                    rain_value=dashboard.get(rk); rain_source="dashboard_data."+rk; break
            if rain_value is not None:
                if isinstance(rain_value,str):
                    rain_value = 1 if rain_value.strip().lower() in {"1","true","yes","on","rain","raining"} else 0
                else:
                    rain_value = 1 if bool(rain_value) else 0
                device["is_raining"]=rain_value
                device["rain_source"]=rain_source
            result["devices"].append(device)
            source=f"{room_label} / {mlabel}" if room_label else mlabel
            if rain_value is not None:
                add_value(f"module.{mname}.is_raining", rain_value, f"{mlabel} – Regen", "", "Wetter", source)
            module_values = (
                ("battery_percent", "Batterie", "%", "Batterie"),
                ("battery_level", "Batteriestand", "", "Batterie"),
                ("reachable", "Erreichbar", "", "Status"),
                ("rf_strength", "Funkstärke", "", "Funk"),
                ("last_seen", "Zuletzt gesehen", "", "Status"),
                ("firmware", "Firmware", "", "Info"),
                ("firmware_revision", "Firmware-Version", "", "Info"),
                ("mode", "Modus", "", "Status"),
            )
            for key,label,unit,category in module_values:
                if module.get(key) is not None:
                    add_value(f"module.{mname}.{key}", module[key], f"{mlabel} – {label}", unit, category, source)
            if position is not None:
                add_value(f"module.{mname}.position", position, f"{mlabel} – Position", "%", "Position", source)
    return result

def udp_path(value):
    parts=[slug(x) for x in str(value).split(".") if str(x).strip()]
    return ".".join(parts) or "value"

def send_udp(cfg, values, heartbeat):
    if not cfg.get("udp_enabled"):
        return 0
    msno=max(1,int(cfg.get("miniserver_no",1)))
    port=int(cfg.get("udp_port",7000))
    prefix=slug(cfg.get("udp_prefix","velux"))
    rules=cfg.get("udp_messages",{}) if isinstance(cfg.get("udp_messages",{}),dict) else {}
    auto_new=bool(cfg.get("udp_auto_new",True))
    mode=str(cfg.get("udp_send_mode","always") or "always").lower()
    if mode not in ("always","changed"):
        mode="always"
    cache=load(UDP_LAST,{}) if mode=="changed" else {}
    try:
        boot_id=Path("/proc/sys/kernel/random/boot_id").read_text().strip()
    except Exception:
        boot_id="unknown"
    if isinstance(cache,dict) and isinstance(cache.get("values"),dict) and cache.get("boot_id")==boot_id:
        last_sent=cache.get("values",{})
    else:
        # Missing/old cache or a LoxBerry reboot => full initial synchronization.
        last_sent={}
    current={}
    payload={}
    for key,value in values.items():
        rule=rules.get(key)
        enabled=auto_new if not isinstance(rule,dict) else bool(rule.get("enabled",True))
        if not enabled:
            continue
        target=key if not isinstance(rule,dict) else (rule.get("name") or key)
        target=udp_path(target)
        current[target]=value
        if mode=="always" or target not in last_sent or last_sent.get(target)!=value:
            payload[target]=value
    # Heartbeat is intentionally sent on every successful/failed cycle, regardless
    # of the changed-values mode. It is not part of the change cache.
    if cfg.get("heartbeat_enabled",True):
        payload[udp_path(cfg.get("udp_heartbeat_key","heartbeat"))]=heartbeat
    if not payload:
        return 0
    helper=Path(__file__).resolve().parent/"loxberry_bridge.pl"
    r=subprocess.run([str(helper),"send",str(msno),str(port),prefix], input=json.dumps(payload,ensure_ascii=False), capture_output=True,text=True,timeout=30)
    if r.returncode != 0:
        raise RuntimeError("LoxBerry UDP: "+(r.stderr.strip() or r.stdout.strip() or "unbekannter Fehler"))
    if mode=="changed":
        # Update cache only after a successful send. First run (or cache deletion)
        # therefore sends every enabled value once as an initial synchronization.
        save(UDP_LAST,{"boot_id":boot_id,"values":current},0o600)
    log(f"UDP Modus={mode}, Nutzwerte={len([k for k in payload if k != udp_path(cfg.get('udp_heartbeat_key','heartbeat'))])}, Gesamt={len(payload)}")
    try:
        return int((r.stdout or "0").strip())
    except ValueError:
        return len(payload)

def main(force=False, force_login=False):
    # Automatic cadence is controlled by velux_scheduler.py. The scheduler calls
    # this worker with --force, while the web UI can also force an immediate run.
    cfg=load(CONFIG,{})
    if not bool(cfg.get("plugin_enabled", True)):
        log("Plugin ist inaktiv - Abruf übersprungen")
        return 0
    last=load(RUN,{})
    interval=max(1,int(cfg.get("poll_interval_minutes",5)))
    now=time.time()
    last_started=float(last.get("started_at", last.get("timestamp",0)) or 0)
    next_due=last_started + interval*60 if last_started > 0 else 0
    if not force and last_started > 0 and now < next_due:
        return 0
    started=now
    # Store the START time immediately. This prevents the runtime of the cloud
    # request from extending the configured polling interval by another cron minute.
    save(RUN,{"started_at":started,"timestamp":started,"ok":None},0o644)
    log(f"Scheduler: Intervall={interval} min, Start={time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(started))}, nächster Lauf ab {time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(started+interval*60))}")
    try:
        from velux_api import login, refresh, homesdata, homestatus
        globals().update(login=login, refresh=refresh, homesdata=homesdata, homestatus=homestatus)
        log(f"Worker gestartet (Python {sys.version.split()[0]}), config={CONFIG}, data={DATA}, log={LOG}")
        log(f"Konfiguration gelesen: email={'ja' if bool(str(cfg.get('email','')).strip()) else 'nein'}, passwort={'ja' if bool(str(cfg.get('password','')).strip()) else 'nein'}")
        tok, token_source=ensure_token(cfg, force_login=force_login)
        log(f"Token OK ({token_source}), homesdata wird abgerufen")
        raw=homesdata(tok["access_token"]); save(RAW_HOMES,raw,0o600)
        homes=extract_homes(raw)
        log(f"homesdata OK, {len(homes)} Home(s) gefunden")
        statuses={}
        for home in homes:
            hid=home.get("id","")
            try:
                statuses[hid]=homestatus(tok["access_token"],hid)
                log(f"homestatus OK: {home.get('name',hid)}")
            except Exception as e:
                statuses[hid]={"error":str(e)}
                log(f"homestatus FEHLER {home.get('name',hid)}: {e}")
        save(RAW_STATUS,statuses,0o600)
        state=flatten(raw,statuses)
        # Diagnostic visibility: log raw room/module keys plus every normalized
        # value that the plugin exposes. This intentionally excludes credentials/tokens.
        for hid,status in statuses.items():
            home_raw=((status.get("body") or {}).get("home") or {}) if isinstance(status,dict) else {}
            for room in (home_raw.get("rooms") or []):
                if isinstance(room,dict):
                    log(f"RAW Raum {room.get('name') or room.get('id','?')}: Felder={','.join(sorted(map(str,room.keys())))}")
            for module in (home_raw.get("modules") or []):
                if isinstance(module,dict):
                    log(f"RAW Modul {module.get('module_name') or module.get('name') or module.get('id','?')}: Typ={module.get('type','?')}, Felder={','.join(sorted(map(str,module.keys())))}")
        for key in sorted(state.get("values",{})):
            meta=state.get("value_meta",{}).get(key,{})
            unit=meta.get("unit","")
            log(f"WERT {key}={state['values'][key]}{(' '+unit) if unit else ''}")
        state.update({"ok":True,"timestamp":int(time.time()),"duration_ms":int((time.time()-started)*1000),"error":"","token_source":token_source})
        # VELUX cloud retrieval and UDP transport are intentionally separated:
        # a Miniserver/UDP problem must not discard otherwise valid VELUX data.
        state["udp_messages"]=0
        state["udp_error"]=""
        try:
            state["udp_messages"]=send_udp(cfg,state["values"],1)
        except Exception as udp_e:
            state["udp_error"]=str(udp_e)
            log("UDP-WARNUNG: "+str(udp_e))
        save(STATE,state,0o644); save(RUN,{"started_at":started,"timestamp":started,"finished_at":time.time(),"ok":True},0o644)
        log(f"Abruf OK: {len(state['homes'])} Home(s), {len(state['devices'])} Gerät(e), {len(state['values'])} Wert(e), UDP={state['udp_messages']}")
        return 0
    except Exception as e:
        err=f"{type(e).__name__}: {e}"
        tb=traceback.format_exc()
        log("FEHLER: "+err)
        log(tb.rstrip())
        try: send_udp(cfg,{},0)
        except Exception as udp_e: log("Heartbeat-Fehler: "+str(udp_e))
        state_err={"ok":False,"timestamp":int(time.time()),"duration_ms":int((time.time()-started)*1000),"error":err,"traceback":tb,"homes":[],"devices":[],"values":{}}
        try: save(STATE,state_err,0o644)
        except Exception as state_e:
            sys.stderr.write(f"STATE SCHREIBFEHLER: {state_e}\n{tb}\n")
        try: save(RUN,{"started_at":started,"timestamp":started,"finished_at":time.time(),"ok":False},0o644)
        except Exception as run_e: sys.stderr.write(f"RUN SCHREIBFEHLER: {run_e}\n")
        sys.stderr.write(err+"\n")
        return 1

if __name__=="__main__":
    raise SystemExit(main("--force" in sys.argv, "--force-login" in sys.argv))
