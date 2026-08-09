#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,os,sys,time,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from velux_api import login,refresh,trigger_gateway_key_retrieval
from pairing import retrieve_signing_key

PLUGIN="veluxactive"
CFG=Path(os.environ.get("LBPCONFIGDIR") or f"/opt/loxberry/config/plugins/{PLUGIN}")
DATA=Path(os.environ.get("LBPDATADIR") or f"/opt/loxberry/data/plugins/{PLUGIN}")
LOG=Path(os.environ.get("LBPLOGDIR") or f"/opt/loxberry/log/plugins/{PLUGIN}")
CONFIG=CFG/"config.json"; TOKENS=CFG/"tokens.json"; STATE=DATA/"state.json"; LOGFILE=LOG/"veluxactive.log"

def load(p,d):
    try:return json.loads(p.read_text(encoding="utf-8"))
    except:return d
def save(p,o,mode=None):
    p.parent.mkdir(parents=True,exist_ok=True); t=p.with_suffix(p.suffix+".tmp")
    t.write_text(json.dumps(o,indent=2,ensure_ascii=False),encoding="utf-8"); t.replace(p)
    if mode is not None: os.chmod(p,mode)
def log(x):
    LOG.mkdir(parents=True,exist_ok=True)
    with LOGFILE.open("a",encoding="utf-8") as f:f.write(time.strftime("%Y-%m-%d %H:%M:%S ")+str(x)+"\n")
def get_token(cfg):
    t=load(TOKENS,{})
    if t.get("access_token") and int(t.get("expires_at",0))>time.time()+120:return t
    if t.get("refresh_token"):
        try:
            n=refresh(t["refresh_token"]); n.setdefault("refresh_token",t["refresh_token"]); save(TOKENS,n,0o600); return n
        except: pass
    n=login(cfg.get("email",""),cfg.get("password","")); save(TOKENS,n,0o600); return n

def choose_gateway(state,gateway_id=None):
    gs=[d for d in state.get("devices",[]) if str(d.get("type","")).upper()=="NXG"]
    if gateway_id:
        gs=[g for g in gs if g.get("id")==gateway_id]
    if len(gs)!=1: raise RuntimeError(f"Gateway nicht eindeutig gefunden ({len(gs)} NXG)")
    return gs[0]

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--host",required=True); ap.add_argument("--gateway-id",default="")
    a=ap.parse_args(); cfg=load(CONFIG,{}); state=load(STATE,{})
    g=choose_gateway(state,a.gateway_id or None); home_id=g.get("home_id")
    if not home_id: raise RuntimeError("Gateway hat keine home_id")
    t=get_token(cfg)
    log(f"PAIRING Cloud-Trigger für Gateway {g.get('name')} ({g.get('id')})")
    r=trigger_gateway_key_retrieval(t["access_token"],home_id,g["id"])
    body=r.get("body") if isinstance(r,dict) else None
    errors=body.get("errors") if isinstance(body,dict) else None
    if errors: raise RuntimeError(f"Cloud retrieve_key Fehler: {errors}")
    log(f"PAIRING Cloud-Trigger OK. Warte auf {a.host}:25050")
    key=retrieve_signing_key(a.host,timeout=45,socket_timeout=10)
    sec=cfg.setdefault("signing",{})
    sec.update({"gateway_ip":a.host,"gateway_id":g["id"],"sign_key_id":key.sign_key_id,
                "hash_sign_key":key.hash_sign_key,"paired_at":int(time.time())})
    save(CONFIG,cfg,0o600)
    log(f"PAIRING OK: Gateway {g['id']}, Sign Key ID gespeichert")
    print(json.dumps({"ok":True,"gateway":g.get("name"),"gateway_id":g["id"],"host":a.host},ensure_ascii=False))
    return 0
if __name__=="__main__":
    try: raise SystemExit(main())
    except Exception as e:
        print(json.dumps({"ok":False,"error":f"{type(e).__name__}: {e}"},ensure_ascii=False))
        try: log("PAIRING FEHLER: "+traceback.format_exc().rstrip())
        except: pass
        raise SystemExit(1)
