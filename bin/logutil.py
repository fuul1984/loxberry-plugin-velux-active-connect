#!/usr/bin/env python3
from __future__ import annotations
import fcntl, os, time
from pathlib import Path

PLUGIN = "veluxactive"
LOG = Path(os.environ.get("LBPLOGDIR") or os.environ.get("LBPLOG") or f"/opt/loxberry/log/plugins/{PLUGIN}")
DATA = Path(os.environ.get("LBPDATADIR") or os.environ.get("LBPDATA") or f"/opt/loxberry/data/plugins/{PLUGIN}")
LOGFILE = LOG / "veluxactive.log"
LOCKFILE = DATA / "log.lock"
DATEFILE = DATA / "log_date"
MAX_BYTES = 1_000_000
KEEP_BYTES = 750_000

def _today() -> str:
    return time.strftime("%Y-%m-%d")

def _locked():
    DATA.mkdir(parents=True, exist_ok=True)
    fh = LOCKFILE.open("a+")
    fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
    return fh

def _trim_locked() -> None:
    if not LOGFILE.exists() or LOGFILE.stat().st_size <= MAX_BYTES:
        return
    with LOGFILE.open("rb") as src:
        size = src.seek(0, os.SEEK_END)
        src.seek(max(0, size - KEEP_BYTES))
        data = src.read()
    # Start at the next complete line after cutting the head.
    if size > KEEP_BYTES:
        nl = data.find(b"\n")
        if nl >= 0:
            data = data[nl + 1:]
    tmp = LOGFILE.with_suffix(".log.tmp")
    with tmp.open("wb") as dst:
        dst.write(data[-KEEP_BYTES:])
    os.chmod(tmp, 0o644)
    tmp.replace(LOGFILE)

def maintain_daily() -> bool:
    """Reset the log once per local calendar day and enforce the size ceiling."""
    LOG.mkdir(parents=True, exist_ok=True)
    lock = _locked()
    try:
        today = _today()
        try:
            stored = DATEFILE.read_text(encoding="utf-8").strip()
        except Exception:
            stored = ""
        if stored != today:
            LOGFILE.write_text("", encoding="utf-8")
            os.chmod(LOGFILE, 0o644)
            tmp = DATEFILE.with_suffix(".tmp")
            tmp.write_text(today + "\n", encoding="utf-8")
            tmp.replace(DATEFILE)
            return True
        _trim_locked()
        return False
    finally:
        fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
        lock.close()

def log(msg) -> bool:
    line = (time.strftime("%Y-%m-%d %H:%M:%S ") + str(msg) + "\n").encode("utf-8", errors="replace")
    LOG.mkdir(parents=True, exist_ok=True)
    lock = _locked()
    try:
        # Daily reset is also checked here so standalone CGI/control calls are safe.
        today = _today()
        try:
            stored = DATEFILE.read_text(encoding="utf-8").strip()
        except Exception:
            stored = ""
        if stored != today:
            LOGFILE.write_text("", encoding="utf-8")
            os.chmod(LOGFILE, 0o644)
            tmp = DATEFILE.with_suffix(".tmp")
            tmp.write_text(today + "\n", encoding="utf-8")
            tmp.replace(DATEFILE)
        current = LOGFILE.stat().st_size if LOGFILE.exists() else 0
        if current + len(line) > MAX_BYTES:
            _trim_locked_force = True
            if LOGFILE.exists():
                with LOGFILE.open("rb") as src:
                    size = src.seek(0, os.SEEK_END)
                    src.seek(max(0, size - KEEP_BYTES))
                    data = src.read()
                if size > KEEP_BYTES:
                    nl = data.find(b"\n")
                    if nl >= 0:
                        data = data[nl + 1:]
                with LOGFILE.open("wb") as dst:
                    dst.write(data[-KEEP_BYTES:])
        with LOGFILE.open("ab") as f:
            f.write(line)
        # Defensive final ceiling for unexpectedly huge single messages.
        if LOGFILE.stat().st_size > MAX_BYTES:
            with LOGFILE.open("rb") as src:
                src.seek(-MAX_BYTES, os.SEEK_END)
                data = src.read(MAX_BYTES)
            nl = data.find(b"\n")
            if nl >= 0:
                data = data[nl + 1:]
            with LOGFILE.open("wb") as dst:
                dst.write(data)
        return True
    except Exception:
        return False
    finally:
        fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
        lock.close()
