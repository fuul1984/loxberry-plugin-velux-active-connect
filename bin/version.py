from pathlib import Path
import os, re

def _read_version(path: Path):
    try:
        text = path.read_text(encoding="utf-8")
        m = re.search(r"^VERSION\s*=\s*([^\s#]+)", text, re.M)
        return m.group(1).strip() if m else None
    except Exception:
        return None

def plugin_version() -> str:
    """Read plugin version from plugin.cfg; plugin.cfg is the single source of truth."""
    here = Path(__file__).resolve()
    lbroot = Path(os.environ.get("LBHOMEDIR", "/opt/loxberry"))

    candidates = [
        # Git/repo layout: <repo>/bin/version.py -> <repo>/plugin.cfg
        here.parent.parent / "plugin.cfg",
        # Installed plugin metadata locations used by LoxBerry setups
        lbroot / "config/plugins/veluxactive/plugin.cfg",
        lbroot / "data/plugins/veluxactive/plugin.cfg",
        lbroot / "bin/plugins/veluxactive/plugin.cfg",
        lbroot / "webfrontend/htmlauth/plugins/veluxactive/plugin.cfg",
        # Plugin package root if explicitly exposed by environment
        Path(os.environ.get("LBPPLUGINDIR", "")) / "plugin.cfg" if os.environ.get("LBPPLUGINDIR") else None,
    ]

    for path in candidates:
        if path is None:
            continue
        version = _read_version(path)
        if version:
            return version

    # Never hardcode a release number here. If the central metadata cannot be
    # resolved, show an explicit neutral value instead of a stale version.
    return "unbekannt"
