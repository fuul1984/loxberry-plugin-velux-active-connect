#!/usr/bin/env python3
from __future__ import annotations
import fcntl, hashlib, json, os, socket, sys, time, traceback
from pathlib import Path
from logutil import log
sys.path.insert(0,str(Path(__file__).resolve().parent))
from velux_api import login,refresh,set_cover_position,stop_cover,signed_position,VeluxError,signed_home_scenario,set_window_mode

PLUGIN="veluxactive"
CFG=Path(os.environ.get("LBPCONFIGDIR") or f"/opt/loxberry/config/plugins/{PLUGIN}")
DATA=Path(os.environ.get("LBPDATADIR") or f"/opt/loxberry/data/plugins/{PLUGIN}")
LOG=Path(os.environ.get("LBPLOGDIR") or f"/opt/loxberry/log/plugins/{PLUGIN}")
CONFIG=CFG/"config.json"; TOKENS=CFG/"tokens.json"; STATE=DATA/"state.json"
CONTROL_STATE=DATA/"control_state.json"; HAP_MAPPING=DATA/"hap_device_mapping.json"; HAP_LEARN=DATA/"hap_mapping_pending.json"; RX_STATE=DATA/"control_rx.json"; PIDFILE=DATA/"control_listener.pid"; LOGFILE=LOG/"veluxactive.log"; API_LOCK=DATA/"api.lock"

def load(p,d):
    try:return json.loads(p.read_text(encoding="utf-8"))
    except Exception:return d
def save(p,o,mode=0o600):
    p.parent.mkdir(parents=True,exist_ok=True)
    t=p.with_suffix(p.suffix+".tmp")
    t.write_text(json.dumps(o,indent=2,ensure_ascii=False),encoding="utf-8")
    os.chmod(t,mode)
    t.replace(p)
def _token_diag(t, source):
    """Log only non-secret OAuth timing metadata for control diagnostics."""
    now=int(time.time())
    try: obtained=int(t.get("obtained_at",0) or 0)
    except Exception: obtained=0
    try: expires=int(t.get("expires_at",0) or 0)
    except Exception: expires=0
    age=(now-obtained) if obtained else -1
    remaining=(expires-now) if expires else -1
    log(
        "CONTROL AUTH DIAG: "
        f"source={source}, token_age_s={age}, expires_in_s={remaining}, "
        f"obtained_at={obtained or 'unknown'}, expires_at={expires or 'unknown'}, "
        f"refresh_token_vorhanden={'ja' if bool(t.get('refresh_token')) else 'nein'}"
    )

def token(cfg):
    t=load(TOKENS,{})
    if t.get("access_token") and int(t.get("expires_at",0))>time.time()+1800:
        _token_diag(t,"cache")
        return t
    if t.get("refresh_token"):
        try:
            log("CONTROL AUTH DIAG: Token abgelaufen/nahe Ablauf - Refresh wird versucht")
            n=refresh(t["refresh_token"]); n.setdefault("refresh_token",t["refresh_token"]); save(TOKENS,n)
            _token_diag(n,"refresh")
            return n
        except Exception as e:log("CONTROL Token refresh fehlgeschlagen: "+str(e))
    password=str(cfg.get("password","") or "")
    if not password:
        raise RuntimeError("Token-Erneuerung nicht möglich. Bitte VELUX-Passwort in den Einstellungen erneut eingeben.")
    log("CONTROL AUTH DIAG: Vollständige Anmeldung wird versucht")
    n=login(cfg.get("email",""),password); save(TOKENS,n)
    _token_diag(n,"login")
    return n

def _is_code6_error(exc):
    txt=str(exc)
    return ("code': 6" in txt or '"code":6' in txt or '"code": 6' in txt)

def _code6_retry(label, call):
    """Retry only transient gateway code 6 for safe close/stop commands.

    Delays are intentionally staggered; other API/signing errors are never retried.
    """
    delays=(5, 15)
    total=1+len(delays)
    for attempt in range(1,total+1):
        try:
            response=call()
            if attempt>1:
                log(f"CONTROL RETRY Code 6: {label} bei Versuch {attempt}/{total} akzeptiert")
            return response
        except VeluxError as e:
            if not _is_code6_error(e) or attempt>=total:
                if _is_code6_error(e) and attempt>=total:
                    log(f"CONTROL RETRY Code 6: {label} nach {total} Versuchen weiterhin abgelehnt")
                raise
            delay=delays[attempt-1]
            log(f"CONTROL RETRY Code 6: {label} Versuch {attempt}/{total} abgelehnt – neuer Versuch in {delay}s")
            time.sleep(delay)

def _is_window_device(d):
    """Identify roof windows without treating all NXO actors as windows.

    VELUX reports windows and shutters with the same generic module type on
    some gateways. Window-only rain/secure positions are the strongest signal
    available in our normalized state; names are only a compatibility fallback.
    """
    if d.get("rain_position") is not None or d.get("secure_position") is not None:
        return True
    name=str(d.get("name","") or "").lower()
    return any(word in name for word in ("fenster","window","fenetre","fenêtre","raam","finestra"))

def parse_message(text,prefix):
    text=text.strip().strip("\x00")
    # Accept "velux.cmd.device.open=1", optional leading '<' used by some Loxone UDP templates.
    if text.startswith("<"): text=text[1:]
    if "=" not in text:return None
    key,value=text.split("=",1); key=key.strip(); value=value.strip()
    p=prefix.rstrip(".")+"."
    if not key.startswith(p):return None
    rest=key[len(p):]
    if "." not in rest:return None
    device,command=rest.rsplit(".",1)
    return device.strip(),command.lower().strip(),value

def _execute_cloud_unlocked(cfg,device_key,command,value):
    if not bool(cfg.get("plugin_enabled", True)):
        raise RuntimeError("Plugin ist inaktiv")
    state=load(STATE,{})
    if command in ("automation","resume_automation","home"):
        devices=state.get("devices",[]) if isinstance(state.get("devices"),list) else []
        # If a specific actor key is provided, enable only that window.
        if device_key not in ("velux_active","all","home",""):
            targets=[d for d in devices if str(d.get("udp_key"))==device_key and d.get("role")=="Aktor"]
        else:
            # Global helper: enable every actuator currently reporting a VELUX algorithm mode.
            targets=[d for d in devices if d.get("role")=="Aktor" and str(d.get("mode","")).startswith("algo") or (d.get("role")=="Aktor" and d.get("mode")=="manual")]
        if not targets:
            raise RuntimeError("Kein VELUX Fenster für Automatisierung gefunden")
        t=token(cfg)
        changed=[]
        for d in targets:
            home_id=d.get("home_id","")
            module_id=d.get("id","")
            bridge_id=d.get("bridge","")
            if not home_id or not module_id or not bridge_id:
                continue
            log(f"CONTROL AUTO: setze {d.get('name',module_id)} mode=algo_available")
            set_window_mode(t["access_token"],home_id,module_id,bridge_id,"algo_available")
            changed.append(d.get("name",module_id))
        if not changed:
            raise RuntimeError("Automatisierung konnte keinem Fenster zugeordnet werden")
        pseudo={"name":"VELUX ACTIVE","key":"velux_active","id":"automation","role":"Automation"}
        return "Automatisierung aktiviert: "+", ".join(changed),pseudo
    devices=[d for d in state.get("devices",[]) if str(d.get("udp_key"))==device_key]
    if len(devices)!=1: raise RuntimeError(f"Gerät '{device_key}' nicht eindeutig gefunden")
    d=devices[0]
    if d.get("role")!="Aktor": raise RuntimeError(f"Gerät '{device_key}' ist kein Aktor")
    is_window=_is_window_device(d)
    signing=cfg.get("signing",{}) if isinstance(cfg.get("signing"),dict) else {}
    if command in ("open","position") and is_window:
        paired=bool(signing.get("sign_key_id") and signing.get("hash_sign_key"))
        log(
            "CONTROL DIAG: "
            f"cmd={command}, home_id={d.get('home_id','')}, "
            f"device_id={d.get('id','')}, bridge_id={d.get('bridge','')}, "
            f"gateway_id={signing.get('gateway_id','')}, gekoppelt={'ja' if paired else 'nein'}"
        )
    if command in ("open","close","stop") and str(value).lower() in ("0","false","off",""):
        return "ignoriert (Trigger=0)",d
    if command=="open": pos=100
    elif command=="close": pos=0
    elif command=="position":
        pos=int(float(value))
        if not 0<=pos<=100: raise ValueError("Position muss 0..100 sein")
    elif command=="stop": pos=None
    else: raise ValueError(f"Unbekannter Befehl '{command}'")
    t=token(cfg)
    if command=="stop":
        response=_code6_retry(
            f"{d.get('name',device_key)} stop",
            lambda: stop_cover(t["access_token"],d.get("home_id",""),d.get("id",""),d.get("bridge",""))
        )
    else:
        try:
            # KIG 300: open is just target_position=100. A signed position
            # command is already verified on this installation, while the
            # normal Netatmo setstate returns code 9 for opening. Force only
            # OPEN into the existing signed fallback by treating that known
            # normal-path failure locally. POSITION keeps its proven behaviour.
            if command == "open" and is_window:
                log("CONTROL KIG300 OPEN: direkter signierter Fensterpfad target=100")
                raise VeluxError("setstate API-Fehler: [{'code': 9, 'id': 'kig300-open-direct'}]")
            if command == "position":
                log("CONTROL DIAG: normaler setstate wird versucht")
            if command == "close":
                response=_code6_retry(
                    f"{d.get('name',device_key)} close",
                    lambda: set_cover_position(t["access_token"],d.get("home_id",""),d.get("id",""),d.get("bridge",""),pos)
                )
            else:
                response=set_cover_position(t["access_token"],d.get("home_id",""),d.get("id",""),d.get("bridge",""),pos)
            result="akzeptiert"
            if command == "position":
                log("CONTROL DIAG: normaler setstate akzeptiert")
        except VeluxError as e:
            if command in ("open","position") and is_window:
                log(f"CONTROL DIAG: normaler setstate Fehler: {e}")
            signing=cfg.get("signing",{}) if isinstance(cfg.get("signing"),dict) else {}
            errtxt=str(e)
            needs_signed=("code': 9" in errtxt or '"code":9' in errtxt or '"code": 9' in errtxt)

            # KIG-300 protection: code 6 points at the gateway and a second
            # identical request did not improve the observed failures. Do not
            # send an automatic retry; return the original API error instead.
            is_code6=("code': 6" in errtxt or '"code":6' in errtxt or '"code": 6' in errtxt)
            if is_code6 and command in ("open","position") and is_window:
                log("CONTROL KIG300 SCHUTZ: Code 6 erkannt – kein automatischer Retry")
                raise

            if not is_window or not needs_signed or not signing.get("sign_key_id") or not signing.get("hash_sign_key"):
                raise
            bridge=d.get("bridge") or signing.get("gateway_id","")
            if signing.get("gateway_id") and bridge and bridge!=signing.get("gateway_id"):
                raise RuntimeError("Signierschlüssel gehört zu einem anderen Gateway")
            if command in ("open","position") and is_window:
                # Record the already-known KIG300/device state and safe request metadata.
                # This is diagnostic only and must never trigger another API request.
                all_devices=state.get("devices",[]) if isinstance(state.get("devices"),list) else []
                gateway_state=next((x for x in all_devices if str(x.get("id",""))==str(bridge)), {})
                log(
                    "CONTROL KIG300 DIAG PRE: "
                    f"home_id={d.get('home_id','')}, device_id={d.get('id','')}, bridge_id={bridge}, "
                    f"device_position={d.get('position',d.get('current_position','?'))}, device_mode={d.get('mode','?')}, "
                    f"device_reachable={d.get('reachable','?')}, gateway_reachable={gateway_state.get('reachable','?')}, "
                    f"gateway_pairing_state={gateway_state.get('pairing_state','?')}, gateway_secure={gateway_state.get('secure','?')}, "
                    f"gateway_busy={gateway_state.get('busy','?')}, gateway_locked={gateway_state.get('locked','?')}, "
                    f"gateway_locking={gateway_state.get('locking','?')}, gateway_last_reset_type={gateway_state.get('last_reset_type','?')}, "
                    f"gateway_calibrating={gateway_state.get('calibrating','?')}, gateway_wifi_state={gateway_state.get('wifi_state','?')}, "
                    f"gateway_wifi_strength={gateway_state.get('wifi_strength','?')}, gateway_last_seen={gateway_state.get('last_seen','?')}"
                )
                # Key-consistency diagnostic: log only a one-way SHA-256 fingerprint
                # and basic metadata, never the signing secret itself.
                hash_key=str(signing.get("hash_sign_key","") or "")
                hash_key_fp=hashlib.sha256(hash_key.encode("utf-8")).hexdigest()[:16] if hash_key else "-"
                log(
                    "CONTROL KIG300 KEYDIAG: "
                    f"sign_key_id={signing.get('sign_key_id','')}, hash_key_sha256_16={hash_key_fp}, "
                    f"hash_key_len={len(hash_key)}, gateway_id={signing.get('gateway_id','')}"
                )
                log(
                    "CONTROL DIAG: signierter setstate wird versucht, "
                    f"bridge_id={bridge}, key_id_vorhanden={'ja' if bool(signing.get('sign_key_id')) else 'nein'}, "
                    f"hash_key_vorhanden={'ja' if bool(signing.get('hash_sign_key')) else 'nein'}"
                )
            try:
                request_started=time.time()
                log(
                    "CONTROL AUTH DIAG: signed_request "
                    f"local_epoch={int(request_started)}, api=syncapi/v1/setstate, "
                    f"app_version=791302006, user_agent=VELUX-Active-Connect-LoxBerry, "
                    f"home_id={d.get('home_id','')}, device_id={d.get('id','')}, bridge_id={bridge}"
                )
                response=signed_position(t["access_token"],d.get("home_id",""),d.get("id",""),bridge,pos,
                                         signing["sign_key_id"],signing["hash_sign_key"])
                diag=response.get("_loxberry_sign_diag",{}) if isinstance(response,dict) else {}
                log(f"CONTROL KIG300 DIAG: signed OK timestamp={diag.get('timestamp','?')}, nonce={diag.get('nonce','?')}, target={diag.get('target_position',pos)}, duration_ms={int((time.time()-request_started)*1000)}")
                result="akzeptiert (signiert)"
                if command in ("open","position"):
                    log("CONTROL DIAG: signierter setstate akzeptiert")
            except VeluxError as signed_e:
                signed_txt=str(signed_e)
                is_code28=("code': 28" in signed_txt or '"code":28' in signed_txt or '"code": 28' in signed_txt)
                if not is_code28 or command not in ("open","position") or not is_window:
                    raise
                # KIG-300: code 28 has repeatedly remained code 28 after a freshly
                # signed retry. Do not send a second command to the gateway; keep the
                # diagnostic evidence and return the original error instead.
                log(f"CONTROL KIG300 DIAG: signed FEHLER code=28, local_epoch={int(time.time())}, device_id={d.get('id','')}, bridge_id={bridge}, target={pos}; kein automatischer Retry")
                raise
        return result,d
    return ("akzeptiert" if response.get("status") in (None,"ok") else str(response.get("status"))),d

def execute(cfg,device_key,command,value):
    # KIG300 protection: never overlap a control request with worker/cloud API traffic.
    # Older logs show signed commands can succeed with the existing signing format;
    # therefore serialize access before changing nonce/timestamp/signature semantics.
    DATA.mkdir(parents=True,exist_ok=True)
    lockfh=API_LOCK.open("a+")
    deadline=time.monotonic()+30.0
    waited=False
    try:
        while True:
            try:
                fcntl.flock(lockfh.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if not waited:
                    log("CONTROL KIG300 API-SCHUTZ: Worker/API-Zugriff aktiv - Steuerbefehl wartet")
                    waited=True
                if time.monotonic() >= deadline:
                    raise RuntimeError("VELUX API ist noch beschäftigt. Bitte Steuerbefehl erneut versuchen.")
                time.sleep(0.25)
        if waited:
            log("CONTROL KIG300 API-SCHUTZ: API frei - Steuerbefehl wird jetzt ausgeführt")
        # Productive control routing. Automation and STOP stay on the proven cloud path.
        if command not in ("open", "close", "position"):
            result, dev = _execute_cloud_unlocked(cfg,device_key,command,value)
            return f"Cloud: {result}", dev

        # Productive final routing is always Local-first. The old selectable Cloud-first
        # mode is intentionally ignored for update compatibility; Cloud remains the
        # automatic fallback and the only route for commands not exposed writable by HAP.
        primary="direct"

        def direct_control():
            st=load(STATE,{})
            acts=[d for d in st.get("devices",[]) if d.get("role")=="Aktor"]
            matches=[d for d in acts if str(d.get("udp_key"))==device_key]
            if len(matches)!=1: raise RuntimeError(f"Gerät '{device_key}' nicht eindeutig gefunden")
            if command in ("open","close") and str(value).lower() in ("0","false","off",""):
                return "ignoriert (Trigger=0)", matches[0]
            pos=100 if command=="open" else 0 if command=="close" else int(float(value))
            if not 0 <= pos <= 100: raise ValueError("Position muss 0..100 sein")
            aid=None
            if len(acts)>1:
                mapping=load(HAP_MAPPING,{})
                hits=[]
                for ma,entry in mapping.items() if isinstance(mapping,dict) else []:
                    if isinstance(entry,dict) and str(entry.get("device_key",""))==str(device_key): hits.append(ma)
                if len(hits)!=1:
                    raise RuntimeError("Direktsteuerung ist für dieses VELUX-Gerät noch nicht eindeutig gelernt")
                aid=int(hits[0])
            from hap_control_test import write_position
            out=write_position(pos,aid=aid)
            log(f"CONTROL DIRECT OK: {matches[0].get('name',device_key)} {command}={value} -> HAP {out.get('characteristic')} target={pos}")
            return f"Direkt (HAP): target={pos} über {out.get('characteristic')}", matches[0]

        def arm_mapping_learning():
            st=load(STATE,{})
            acts=[d for d in st.get("devices",[]) if d.get("role")=="Aktor"]
            matches=[d for d in acts if str(d.get("udp_key"))==device_key]
            if len(acts)<=1 or len(matches)!=1: return
            try:
                pos=100 if command=="open" else 0 if command=="close" else int(float(value))
            except Exception: return
            position_key=f"module.{device_key}.position"
            vals=st.get("values",{}) if isinstance(st,dict) else {}
            if position_key not in vals:
                candidates=[k for k in vals if str(k).startswith("module.") and str(k).endswith(".position") and str(device_key) in str(k)]
                if len(candidates)==1: position_key=candidates[0]
            save(HAP_LEARN,{"device_key":device_key,"position_key":position_key,"target":pos,"created_at":time.time(),"expires_at":time.time()+15},0o664)
            # The pending record is the only bridge between cloud fallback and HAP event
            # correlation. It is deliberately short-lived and contains no credentials.
            log(f"CONTROL HAP MAP LEARN ARM: {device_key} target={pos} -> warte auf eindeutiges Eventstream-Target")

        if primary=="direct":
            try:
                return direct_control()
            except Exception as direct_e:
                log(f"CONTROL DIRECT FEHLER: {type(direct_e).__name__}: {direct_e}; Cloud-Fallback wird versucht")
                try:
                    arm_mapping_learning()
                    try:
                        result, dev=_execute_cloud_unlocked(cfg,device_key,command,value)
                    except Exception:
                        # A failed cloud command must never leave a learn window armed.
                        try: HAP_LEARN.unlink()
                        except FileNotFoundError: pass
                        except Exception as cleanup_e: log(f"CONTROL HAP MAP CLEANUP WARNUNG: {cleanup_e}")
                        raise
                    return f"Direkt fehlgeschlagen ({direct_e}) -> Cloud-Fallback: {result}", dev
                except Exception as cloud_e:
                    raise RuntimeError(f"Direkt fehlgeschlagen: {direct_e}; Cloud-Fallback fehlgeschlagen: {cloud_e}") from cloud_e
        else:
            try:
                arm_mapping_learning()
                try:
                    result, dev=_execute_cloud_unlocked(cfg,device_key,command,value)
                except Exception:
                    try: HAP_LEARN.unlink()
                    except FileNotFoundError: pass
                    except Exception as cleanup_e: log(f"CONTROL HAP MAP CLEANUP WARNUNG: {cleanup_e}")
                    raise
                return f"Cloud: {result}", dev
            except Exception as cloud_e:
                log(f"CONTROL CLOUD FEHLER: {type(cloud_e).__name__}: {cloud_e}; Direkt-Fallback wird versucht")
                try:
                    result, dev=direct_control()
                    return f"Cloud fehlgeschlagen ({cloud_e}) -> {result}", dev
                except Exception as direct_e:
                    raise RuntimeError(f"Cloud fehlgeschlagen: {cloud_e}; Direkt-Fallback fehlgeschlagen: {direct_e}") from direct_e
    finally:
        try: fcntl.flock(lockfh.fileno(),fcntl.LOCK_UN)
        except Exception: pass
        lockfh.close()

def main():
    cfg=load(CONFIG,{})
    c=cfg.get("control",{}) if isinstance(cfg.get("control"),dict) else {}
    if not bool(cfg.get("plugin_enabled", True)) or not c.get("enabled"): return 0
    port=int(c.get("udp_listen_port",7001)); prefix=str(c.get("command_prefix","velux.cmd") or "velux.cmd")
    DATA.mkdir(parents=True,exist_ok=True)
    sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
    sock.bind(("0.0.0.0",port)); sock.settimeout(15)
    # Publish the PID only after the UDP socket is successfully bound.
    PIDFILE.write_text(str(os.getpid()),encoding="utf-8")
    log(f"CONTROL Listener gestartet: UDP {port}, Präfix={prefix}")
    try:
        while True:
            cfg=load(CONFIG,{})
            c=cfg.get("control",{}) if isinstance(cfg.get("control"),dict) else {}
            if not bool(cfg.get("plugin_enabled", True)) or not c.get("enabled") or int(c.get("udp_listen_port",port))!=port: break
            try:data,addr=sock.recvfrom(4096)
            except socket.timeout:continue
            text=data.decode("utf-8","replace").strip()
            allowed=c.get("allowed_senders",[]) if isinstance(c.get("allowed_senders",[]),list) else []
            allowed=[str(x).strip() for x in allowed if str(x).strip()]
            # Localhost is always allowed for the built-in self-test. Network commands
            # are accepted only from explicitly selected Miniserver addresses.
            if addr[0] not in ("127.0.0.1","::1") and (not allowed or addr[0] not in allowed):
                rx={"timestamp":int(time.time()),"source_ip":addr[0],"source_port":addr[1],"text":text,"parsed":False,"rejected":True}
                save(RX_STATE,rx)
                log(f"CONTROL UDP ABGELEHNT {addr[0]}:{addr[1]}: Absender nicht erlaubt")
                continue
            rx={"timestamp":int(time.time()),"source_ip":addr[0],"source_port":addr[1],"text":text,"parsed":False,"rejected":False}
            save(RX_STATE,rx)
            log(f"CONTROL UDP RAW {addr[0]}:{addr[1]}: {text}")
            parsed=parse_message(text,prefix)
            if not parsed:
                log(f"CONTROL UDP IGNORIERT: Präfix/Format passt nicht ({prefix})")
                continue
            dev,cmd,val=parsed
            rx.update({"parsed":True,"device":dev,"command":cmd,"value":val}); save(RX_STATE,rx)
            log(f"CONTROL RX {addr[0]}:{addr[1]}: {text}")
            out={"timestamp":int(time.time()),"command":text,"device":dev,"ok":False,"result":""}
            try:
                result,d=execute(cfg,dev,cmd,val); out.update({"ok":True,"device":d.get("name",dev),"result":result})
                log(f"CONTROL OK: {d.get('name',dev)} {cmd}={val} -> {result}")
            except Exception as e:
                out["result"]=f"{type(e).__name__}: {e}"; log("CONTROL FEHLER: "+out["result"]); log(traceback.format_exc().rstrip())
            save(CONTROL_STATE,out)
    finally:
        sock.close()
        try: PIDFILE.unlink()
        except FileNotFoundError:pass
        log("CONTROL Listener beendet")
    return 0
if __name__=="__main__": raise SystemExit(main())
