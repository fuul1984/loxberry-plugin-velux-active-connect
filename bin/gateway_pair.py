#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,os,sys,time,traceback
from pathlib import Path
from logutil import log
sys.path.insert(0,str(Path(__file__).resolve().parent))
from velux_api import login,refresh,trigger_gateway_key_retrieval
from pairing import retrieve_signing_key

PLUGIN="veluxactive"
CFG=Path(os.environ.get("LBPCONFIGDIR") or f"/opt/loxberry/config/plugins/{PLUGIN}")
DATA=Path(os.environ.get("LBPDATADIR") or f"/opt/loxberry/data/plugins/{PLUGIN}")
LOG=Path(os.environ.get("LBPLOGDIR") or f"/opt/loxberry/log/plugins/{PLUGIN}")
CONFIG=CFG/"config.json"; TOKENS=CFG/"tokens.json"; STATE=DATA/"state.json"; PENDING=DATA/"pairing_pending.json"; LOGFILE=LOG/"veluxactive.log"
PENDING_MAX_AGE=15*60

def load(p,d):
    try:return json.loads(p.read_text(encoding="utf-8"))
    except:return d
def save(p,o,mode=None):
    p.parent.mkdir(parents=True,exist_ok=True); t=p.with_suffix(p.suffix+".tmp")
    t.write_text(json.dumps(o,indent=2,ensure_ascii=False),encoding="utf-8"); t.replace(p)
    if mode is not None: os.chmod(p,mode)
def get_token(cfg):
    t=load(TOKENS,{})
    if t.get("access_token") and int(t.get("expires_at",0))>time.time()+1800:return t
    if t.get("refresh_token"):
        try:
            n=refresh(t["refresh_token"]); n.setdefault("refresh_token",t["refresh_token"]); save(TOKENS,n,0o600); return n
        except: pass
    n=login(cfg.get("email",""),cfg.get("password","")); save(TOKENS,n,0o600); return n

def choose_gateway(state,gateway_id=None):
    gs=[d for d in state.get("devices",[]) if str(d.get("type","")).upper()=="NXG"]
    if gateway_id: gs=[g for g in gs if g.get("id")==gateway_id]
    if len(gs)!=1: raise RuntimeError(f"Gateway nicht eindeutig gefunden ({len(gs)} NXG)")
    return gs[0]

def prepare(host,gateway_id):
    cfg=load(CONFIG,{}); state=load(STATE,{})
    g=choose_gateway(state,gateway_id or None); home_id=g.get("home_id")
    if not home_id: raise RuntimeError("Gateway hat keine home_id")
    t=get_token(cfg)
    log(f"PAIRING PREPARE: Cloud-Trigger für Gateway {g.get('name')} ({g.get('id')})")
    r=trigger_gateway_key_retrieval(t["access_token"],home_id,g["id"])
    body=r.get("body") if isinstance(r,dict) else None
    errors=body.get("errors") if isinstance(body,dict) else None
    if errors: raise RuntimeError(f"Cloud retrieve_key Fehler: {errors}")
    pending={"host":host,"gateway_id":g["id"],"gateway_name":g.get("name",""),"home_id":home_id,"prepared_at":int(time.time())}
    save(PENDING,pending,0o600)
    log(f"PAIRING PREPARE OK: Gateway vorbereitet; warte auf Benutzeraktion am Gateway, danach lokaler Abruf {host}:25050")
    return {"ok":True,"stage":"prepared","gateway":g.get("name"),"gateway_id":g["id"],"host":host}

def fetch():
    pending=load(PENDING,{})
    if not pending.get("host") or not pending.get("gateway_id") or not pending.get("prepared_at"):
        raise RuntimeError("Keine vorbereitete Gateway-Kopplung vorhanden. Bitte zuerst 'Kopplung vorbereiten' ausführen.")
    age=int(time.time())-int(pending.get("prepared_at",0))
    if age<0 or age>PENDING_MAX_AGE:
        try:PENDING.unlink()
        except FileNotFoundError:pass
        raise RuntimeError("Vorbereitete Gateway-Kopplung ist abgelaufen. Bitte erneut vorbereiten.")
    host=pending["host"]
    log(f"PAIRING FETCH: Benutzeraktion bestätigt; rufe Signierschlüssel von {host}:25050 ab")
    # Existing signing data is intentionally left untouched until the complete local exchange succeeds.
    key=retrieve_signing_key(host,timeout=45,socket_timeout=10)
    cfg=load(CONFIG,{})
    sec=cfg.setdefault("signing",{})
    sec.update({"gateway_ip":host,"gateway_id":pending["gateway_id"],"sign_key_id":key.sign_key_id,
                "hash_sign_key":key.hash_sign_key,"paired_at":int(time.time())})
    save(CONFIG,cfg,0o600)
    try:PENDING.unlink()
    except FileNotFoundError:pass
    log(f"PAIRING OK: Gateway {pending['gateway_id']}, Sign Key ID gespeichert")
    return {"ok":True,"stage":"paired","gateway":pending.get("gateway_name"),"gateway_id":pending["gateway_id"],"host":host}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--mode",choices=("prepare","fetch"),default="prepare"); ap.add_argument("--host",default=""); ap.add_argument("--gateway-id",default="")
    a=ap.parse_args()
    if a.mode=="prepare":
        if not a.host: raise RuntimeError("Gateway-IP fehlt")
        result=prepare(a.host,a.gateway_id)
    else: result=fetch()
    print(json.dumps(result,ensure_ascii=False)); return 0

if __name__=="__main__":
    try: raise SystemExit(main())
    except Exception as e:
        print(json.dumps({"ok":False,"error":f"{type(e).__name__}: {e}"},ensure_ascii=False))
        try: log("PAIRING FEHLER: "+traceback.format_exc().rstrip())
        except: pass
        raise SystemExit(1)
