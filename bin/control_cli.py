#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, sys, time, traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from control_listener import execute

PLUGIN="veluxactive"
CFG=Path(os.environ.get("LBPCONFIGDIR") or f"/opt/loxberry/config/plugins/{PLUGIN}")
DATA=Path(os.environ.get("LBPDATADIR") or f"/opt/loxberry/data/plugins/{PLUGIN}")
LOG=Path(os.environ.get("LBPLOGDIR") or f"/opt/loxberry/log/plugins/{PLUGIN}")
CONFIG=CFG/"config.json"
CONTROL_STATE=DATA/"control_state.json"
LOGFILE=LOG/"veluxactive.log"

def load(p,d):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return d

def save(p,o):
    p.parent.mkdir(parents=True,exist_ok=True)
    tmp=p.with_suffix(p.suffix+".tmp")
    tmp.write_text(json.dumps(o,indent=2,ensure_ascii=False),encoding="utf-8")
    tmp.replace(p)

def log(msg):
    try:
        LOG.mkdir(parents=True,exist_ok=True)
        with LOGFILE.open("a",encoding="utf-8") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S ")+str(msg)+"\n")
    except Exception:
        pass

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--device",required=True)
    ap.add_argument("--command",required=True,choices=["open","close","stop","position"])
    ap.add_argument("--value",default="1")
    args=ap.parse_args()

    cfg=load(CONFIG,{})
    out={
        "timestamp":int(time.time()),
        "command":f"WEB {args.device}.{args.command}={args.value}",
        "device":args.device,
        "ok":False,
        "result":"",
        "source":"Web",
    }
    try:
        log(f"CONTROL WEB RX: {args.device}.{args.command}={args.value}")
        result,dev=execute(cfg,args.device,args.command,args.value)
        out.update({"ok":True,"device":dev.get("name",args.device),"result":result})
        log(f"CONTROL WEB OK: {dev.get('name',args.device)} {args.command}={args.value} -> {result}")
        save(CONTROL_STATE,out)
        print(json.dumps(out,ensure_ascii=False))
        return 0
    except Exception as e:
        out["result"]=f"{type(e).__name__}: {e}"
        log("CONTROL WEB FEHLER: "+out["result"])
        log(traceback.format_exc().rstrip())
        save(CONTROL_STATE,out)
        print(json.dumps(out,ensure_ascii=False))
        return 1

if __name__=="__main__":
    raise SystemExit(main())
