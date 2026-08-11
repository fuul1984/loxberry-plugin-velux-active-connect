from pathlib import Path
import os, re

def plugin_version() -> str:
    """Read the plugin version from plugin.cfg (single source of truth)."""
    lbroot=Path(os.environ.get("LBHOMEDIR","/opt/loxberry"))
    candidates=[
        Path(__file__).resolve().parents[1]/"plugin.cfg",
        lbroot/"config/plugins/veluxactive/plugin.cfg",
        lbroot/"bin/plugins/veluxactive/plugin.cfg",
    ]
    for path in candidates:
        try:
            text=path.read_text(encoding="utf-8")
            m=re.search(r"^VERSION\s*=\s*([^\s#]+)",text,re.M)
            if m:
                return m.group(1).strip()
        except Exception:
            pass
    return "unknown"
