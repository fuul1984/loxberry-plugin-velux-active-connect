#!/usr/bin/env python3
import fcntl
import json
import os
import subprocess
import sys
import time
from pathlib import Path

PLUGIN="veluxactive"
LBROOT=Path(os.environ.get("LBHOMEDIR","/opt/loxberry"))
CFG=LBROOT/"config/plugins"/PLUGIN/"config.json"
DATA=LBROOT/"data/plugins"/PLUGIN
LOG=LBROOT/"log/plugins"/PLUGIN
WORKER=LBROOT/"bin/plugins"/PLUGIN/"worker.py"
STATE=DATA/"scheduler_last_success.timestamp"
LOCK=DATA/"scheduler.lock"

DATA.mkdir(parents=True,exist_ok=True)
LOG.mkdir(parents=True,exist_ok=True)

def log(msg):
    with (LOG/"veluxactive.log").open("a",encoding="utf-8") as f:
        f.write(time.strftime("%Y-%m-%d %H:%M:%S")+" "+msg+"\n")

try:
    lockfh=LOCK.open("a+")
    fcntl.flock(lockfh.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
except BlockingIOError:
    raise SystemExit(0)

try:
    cfg=json.loads(CFG.read_text(encoding="utf-8"))
except Exception as e:
    log(f"Scheduler FEHLER: Konfiguration konnte nicht gelesen werden: {e}")
    raise SystemExit(1)

try:
    interval=int(cfg.get("poll_interval_minutes",5))
except Exception:
    interval=5
if interval < 1 or interval > 1440:
    log(f"Scheduler FEHLER: Abrufintervall {interval} ist ungültig (1-1440)")
    raise SystemExit(1)

last_success=0
try:
    raw=STATE.read_text(encoding="utf-8").strip()
    if raw.isdigit():
        last_success=int(raw)
except FileNotFoundError:
    pass
except Exception as e:
    log(f"Scheduler WARNUNG: letzter Erfolgszeitpunkt nicht lesbar: {e}")

now=int(time.time())
if last_success > 0 and (now-last_success) < interval*60:
    raise SystemExit(0)

# Reference point for the interval is the START of this run.
# We only persist it after the worker completed successfully.
run_started=now

if not WORKER.is_file():
    log(f"Scheduler FEHLER: Worker fehlt: {WORKER}")
    raise SystemExit(1)

log(f"Scheduler: Intervall={interval} min, Lauf fällig")
result=subprocess.run(
    ["/usr/bin/python3",str(WORKER),"--force"],
    env={
        **os.environ,
        "LBPCONFIGDIR":str(LBROOT/"config/plugins"/PLUGIN),
        "LBPDATADIR":str(DATA),
        "LBPLOGDIR":str(LOG),
    }
)

if result.returncode != 0:
    log(f"Scheduler: Worker endete mit Fehlercode {result.returncode}; erneuter Versuch beim nächsten Minutenlauf")
    raise SystemExit(result.returncode)

# Only a successful run advances the interval, but the reference timestamp
# is the START of the successful run. This prevents a 1-minute interval from
# becoming 2 minutes when the API call itself takes a few seconds.
tmp=STATE.with_name(STATE.name+f".tmp.{os.getpid()}")
tmp.write_text(str(run_started)+"\n",encoding="utf-8")
os.replace(tmp,STATE)
next_due=run_started + interval*60
log(f"Scheduler: Lauf erfolgreich, nächster Lauf ab {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(next_due))}")
raise SystemExit(0)
