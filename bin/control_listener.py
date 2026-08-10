#!/usr/bin/env python3
from __future__ import annotations
import json, os, socket, sys, time, traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from velux_api import login, refresh, set_cover_position, stop_cover, signed_position, VeluxError

PLUGIN="veluxactive"
CFG=Path(os.environ.get("LBPCONFIGDIR") or f"/opt/loxberry/config/plugins/{PLUGIN}")
DATA=Path(os.environ.get("LBPDATADIR") or f"/opt/loxberry/data/plugins/{PLUGIN}")
LOG=Path(os.environ.get("LBPLOGDIR") or f"/opt/loxberry/log/plugins/{PLUGIN}")
CONFIG=CFG/"config.json"; TOKENS=CFG/"tokens.json"; STATE=DATA/"state.json"
CONTROL_STATE=DATA/"control_state.json"; RX_STATE=DATA/"control_rx.json"; PIDFILE=DATA/"control_listener.pid"; LOGFILE=LOG/"veluxactive.log"

def load(p,d):
    try:return json.loads(p.read_text(encoding="utf-8"))
    except Exception:return d
def save(p,o):
    p.parent.mkdir(parents=True,exist_ok=True)
    t=p.with_suffix(p.suffix+".tmp"); t.write_text(json.dumps(o,indent=2,ensure_ascii=False),encoding="utf-8"); t.replace(p)
def log(m):
    try:
        LOG.mkdir(parents=True,exist_ok=True)
        with LOGFILE.open("a",encoding="utf-8") as f:f.write(time.strftime("%Y-%m-%d %H:%M:%S ")+str(m)+"\n")
    except Exception:pass
def token(cfg):
    t=load(TOKENS,{})
    if t.get("access_token") and int(t.get("expires_at",0))>time.time()+120:return t
    if t.get("refresh_token"):
        try:
            n=refresh(t["refresh_token"]); n.setdefault("refresh_token",t["refresh_token"]); save(TOKENS,n); return n
        except Exception as e:log("CONTROL Token refresh fehlgeschlagen: "+str(e))
    n=login(cfg.get("email",""),cfg.get("password","")); save(TOKENS,n); return n

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

def execute(cfg,device_key,command,value):
    if not bool(cfg.get("plugin_enabled", True)):
        raise RuntimeError("Plugin ist inaktiv")
    state=load(STATE,{})
    if command in ("automation","resume_automation","home"):
        homes=state.get("homes",[]) if isinstance(state.get("homes"),list) else []
        devices=state.get("devices",[]) if isinstance(state.get("devices"),list) else []
        gateways=[d for d in devices if d.get("type")=="NXG" or d.get("role")=="Gateway"]
        signing=cfg.get("signing",{}) if isinstance(cfg.get("signing"),dict) else {}
        gateway_id=signing.get("gateway_id","") or (gateways[0].get("id","") if gateways else "")
        home_id=(gateways[0].get("home_id","") if gateways else "") or (homes[0].get("id","") if homes else "")
        if not gateway_id or not home_id:
            raise RuntimeError("Gateway/Home für Automatisierung nicht gefunden")
        if not signing.get("sign_key_id") or not signing.get("hash_sign_key"):
            raise RuntimeError("Gateway ist nicht vollständig gekoppelt")
        t=ensure_token(cfg)
        log(f"CONTROL AUTO: Automatisierung aktivieren, home_id={home_id}, gateway_id={gateway_id}")
        signed_home_scenario(t["access_token"],home_id,gateway_id,signing["sign_key_id"],signing["hash_sign_key"])
        pseudo={"name":"VELUX ACTIVE","key":"velux_active","id":gateway_id,"home_id":home_id,"role":"Gateway"}
        return "Automatisierung aktiviert (scenario=home, signiert)",pseudo
    devices=[d for d in state.get("devices",[]) if str(d.get("udp_key"))==device_key]
    if len(devices)!=1: raise RuntimeError(f"Gerät '{device_key}' nicht eindeutig gefunden")
    d=devices[0]
    if d.get("role")!="Aktor": raise RuntimeError(f"Gerät '{device_key}' ist kein Aktor")
    if command in ("open","position"):
        signing=cfg.get("signing",{}) if isinstance(cfg.get("signing"),dict) else {}
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
        response=stop_cover(t["access_token"],d.get("home_id",""),d.get("id",""),d.get("bridge",""))
    else:
        try:
            if command in ("open","position"):
                log("CONTROL DIAG: normaler setstate wird versucht")
            response=set_cover_position(t["access_token"],d.get("home_id",""),d.get("id",""),d.get("bridge",""),pos)
            result="akzeptiert"
            if command in ("open","position"):
                log("CONTROL DIAG: normaler setstate akzeptiert")
        except VeluxError as e:
            if command in ("open","position"):
                log(f"CONTROL DIAG: normaler setstate Fehler: {e}")
            signing=cfg.get("signing",{}) if isinstance(cfg.get("signing"),dict) else {}
            needs_signed=("code': 9" in str(e) or '"code":9' in str(e) or '"code": 9' in str(e))
            if not needs_signed or not signing.get("sign_key_id") or not signing.get("hash_sign_key"):
                raise
            bridge=d.get("bridge") or signing.get("gateway_id","")
            if signing.get("gateway_id") and bridge and bridge!=signing.get("gateway_id"):
                raise RuntimeError("Signierschlüssel gehört zu einem anderen Gateway")
            if command in ("open","position"):
                log(
                    "CONTROL DIAG: signierter setstate wird versucht, "
                    f"bridge_id={bridge}, key_id_vorhanden={'ja' if bool(signing.get('sign_key_id')) else 'nein'}, "
                    f"hash_key_vorhanden={'ja' if bool(signing.get('hash_sign_key')) else 'nein'}"
                )
            response=signed_position(t["access_token"],d.get("home_id",""),d.get("id",""),bridge,pos,
                                     signing["sign_key_id"],signing["hash_sign_key"])
            result="akzeptiert (signiert)"
            if command in ("open","position"):
                log("CONTROL DIAG: signierter setstate akzeptiert")
        return result,d
    return ("akzeptiert" if response.get("status") in (None,"ok") else str(response.get("status"))),d

def main():
    cfg=load(CONFIG,{})
    c=cfg.get("control",{}) if isinstance(cfg.get("control"),dict) else {}
    if not bool(cfg.get("plugin_enabled", True)) or not c.get("enabled"): return 0
    port=int(c.get("udp_listen_port",7001)); prefix=str(c.get("command_prefix","velux.cmd") or "velux.cmd")
    DATA.mkdir(parents=True,exist_ok=True); PIDFILE.write_text(str(os.getpid()))
    sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
    sock.bind(("0.0.0.0",port)); sock.settimeout(15)
    log(f"CONTROL Listener gestartet: UDP {port}, Präfix={prefix}")
    try:
        while True:
            cfg=load(CONFIG,{})
            c=cfg.get("control",{}) if isinstance(cfg.get("control"),dict) else {}
            if not bool(cfg.get("plugin_enabled", True)) or not c.get("enabled") or int(c.get("udp_listen_port",port))!=port: break
            try:data,addr=sock.recvfrom(4096)
            except socket.timeout:continue
            text=data.decode("utf-8","replace").strip()
            rx={"timestamp":int(time.time()),"source_ip":addr[0],"source_port":addr[1],"text":text,"parsed":False}
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
