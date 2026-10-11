#!/usr/bin/env python3
from __future__ import annotations
import json, os, time, urllib.parse, urllib.request, urllib.error
from pathlib import Path
from typing import Any
from version import plugin_version

BASE_URL = "https://api.netatmo.com/"
TOKEN_URL = BASE_URL + "oauth2/token"
HOMESDATA_URL = BASE_URL + "api/homesdata"
HOMESTATUS_URL = BASE_URL + "api/homestatus"
SETSTATE_URL = BASE_URL + "api/setstate"
CLIENT_ID = "5931426da127d981e76bdd3f"
CLIENT_SECRET = "6ae2d89d15e767ae5c56b456b452d319"
APP_VERSION = "791302006"
USER_PREFIX = "velux"
SCOPE = "velux_scopes"
USER_AGENT = f"VELUX-Active-Connect-LoxBerry/{plugin_version()}"

class VeluxError(RuntimeError):
    pass

def _read_json(response) -> dict[str, Any]:
    body = response.read().decode("utf-8", "replace")
    try:
        data = json.loads(body)
    except json.JSONDecodeError as e:
        raise VeluxError(f"Ungültige JSON-Antwort: {body[:500]}") from e
    if not isinstance(data, dict):
        raise VeluxError(f"Unerwartete API-Antwort: {data!r}")
    return data

def post_form(url: str, data: dict[str, Any], timeout: int = 20, token: str | None = None) -> dict[str, Any]:
    payload = urllib.parse.urlencode(data).encode("utf-8")
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return _read_json(r)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        raise VeluxError(f"HTTP {e.code}: {body[:1000]}") from e
    except urllib.error.URLError as e:
        raise VeluxError(f"Netzwerkfehler: {e.reason}") from e
    except TimeoutError as e:
        raise VeluxError("Zeitüberschreitung beim VELUX-Cloudzugriff") from e

def post_json(url: str, payload: dict[str, Any], timeout: int = 20, token: str | None = None) -> dict[str, Any]:
    """POST a real JSON body. Netatmo /setstate requires this transport."""
    body = json.dumps(payload, separators=(",",":"), ensure_ascii=False).encode("utf-8")
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return _read_json(r)
    except urllib.error.HTTPError as e:
        response_body = e.read().decode("utf-8", "replace")
        raise VeluxError(f"HTTP {e.code}: {response_body[:1000]}") from e
    except urllib.error.URLError as e:
        raise VeluxError(f"Netzwerkfehler: {e.reason}") from e
    except TimeoutError as e:
        raise VeluxError("Zeitüberschreitung beim VELUX-Cloudzugriff") from e

def login(email: str, password: str) -> dict[str, Any]:
    if not email or not password:
        raise VeluxError("E-Mail und Passwort fehlen")
    data = post_form(TOKEN_URL, {
        "grant_type": "password",
        "username": email,
        "password": password,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "app_version": APP_VERSION,
        "user_prefix": USER_PREFIX,
        "scope": SCOPE,
    })
    if "access_token" not in data:
        raise VeluxError(f"Kein Access Token in der Antwort: {data}")
    now = int(time.time())
    data["obtained_at"] = now
    data["expires_at"] = now + int(data.get("expires_in", 10800))
    return data

def refresh(refresh_token: str) -> dict[str, Any]:
    if not refresh_token:
        raise VeluxError("Refresh Token fehlt")
    data = post_form(TOKEN_URL, {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "app_version": APP_VERSION,
    })
    if "access_token" not in data:
        raise VeluxError(f"Kein Access Token nach Refresh: {data}")
    now = int(time.time())
    data["obtained_at"] = now
    data["expires_at"] = now + int(data.get("expires_in", 10800))
    return data

def homesdata(token: str) -> dict[str, Any]:
    return post_form(HOMESDATA_URL, {}, timeout=25, token=token)

def homestatus(token: str, home_id: str) -> dict[str, Any]:
    if not home_id:
        raise VeluxError("Home-ID fehlt")
    return post_form(HOMESTATUS_URL, {"home_id": home_id}, timeout=25, token=token)


def set_cover_position(token: str, home_id: str, module_id: str, bridge_id: str, position: int) -> dict[str, Any]:
    """Control a VELUX cover through the regular Netatmo/VELUX cloud setstate path."""
    if not 0 <= int(position) <= 100:
        raise VeluxError("Position muss zwischen 0 und 100 liegen")
    module = {"id": module_id, "target_position": int(position)}
    if bridge_id:
        module["bridge"] = bridge_id
    payload = {"home": {"id": home_id, "modules": [module]}}
    data = post_json(SETSTATE_URL, payload, timeout=25, token=token)
    body = data.get("body") if isinstance(data, dict) else None
    errors = body.get("errors") if isinstance(body, dict) else None
    if errors:
        raise VeluxError(f"setstate API-Fehler: {errors}")
    if data.get("status") not in (None, "ok"):
        raise VeluxError(f"setstate fehlgeschlagen: {data}")
    return data

def stop_cover(token: str, home_id: str, module_id: str, bridge_id: str, timezone: str="Europe/Zurich") -> dict[str, Any]:
    """Stop movements using the VELUX app sync API semantics.

    The official app addresses the gateway for stop and sends
    stop_movements=all; it does not emulate stop with target_position=-1.
    """
    if not bridge_id:
        raise VeluxError("Gateway-/Bridge-ID fehlt für Stop")
    payload={"app_version":APP_VERSION,
             "home":{"id":home_id,"timezone":timezone,
                     "modules":[{"id":bridge_id,"stop_movements":"all"}]}}
    data=post_json(SYNC_SETSTATE_URL,payload,timeout=25,token=token)
    body=data.get("body") if isinstance(data,dict) else None
    errors=body.get("errors") if isinstance(body,dict) else None
    if errors:
        raise VeluxError(f"stop setstate API-Fehler: {errors}")
    if data.get("status") not in (None,"ok"):
        raise VeluxError(f"stop setstate fehlgeschlagen: {data}")
    return data


SYNC_SETSTATE_URL = "https://app.velux-active.com/syncapi/v1/setstate"

def trigger_gateway_key_retrieval(token: str, home_id: str, gateway_id: str) -> dict[str, Any]:
    """Put NXG gateway into local signing-key retrieval mode."""
    payload={"home":{"id":home_id,"modules":[{"id":gateway_id,"retrieve_key":True}]}}
    return post_json(SETSTATE_URL,payload,timeout=25,token=token)

def signed_position(token: str, home_id: str, module_id: str, bridge_id: str, position: int,
                    sign_key_id: str, hash_sign_key: str, timezone: str="Europe/Zurich") -> dict[str, Any]:
    from signing import allocate_nonces, build_signed_module
    # Keep nonce allocation shared between the UDP listener and Web/CLI process.
    # Calls are already serialized by control_listener's API_LOCK. Persist the
    # allocation before sending so even a rejected request never reuses a pair.
    data_dir=Path(os.environ.get("LBPDATADIR") or "/opt/loxberry/data/plugins/veluxactive")
    nonce_state_file=data_dir/"signing_nonce.json"
    last_ts=0; last_nonce=-1
    try:
        ns=json.loads(nonce_state_file.read_text(encoding="utf-8"))
        last_ts=int(ns.get("timestamp",0) or 0)
        last_nonce=int(ns.get("nonce",-1))
    except Exception:
        pass
    timestamp,nonce=allocate_nonces(int(time.time()),last_ts,last_nonce)
    nonce_state_file.parent.mkdir(parents=True,exist_ok=True)
    tmp=nonce_state_file.with_suffix(".json.tmp")
    tmp.write_text(json.dumps({"timestamp":timestamp,"nonce":nonce}),encoding="utf-8")
    os.chmod(tmp,0o600)
    tmp.replace(nonce_state_file)
    mod=build_signed_module(module_id,position,bridge_id,sign_key_id,hash_sign_key,timestamp=timestamp,nonce=nonce)
    # Safe diagnostics for KIG 300: expose request metadata needed to compare
    # accepted/rejected signed calls, but never log or return secret key/hash material.
    diag={
        "timestamp": mod.get("timestamp"),
        "nonce": mod.get("nonce"),
        "module_id": module_id,
        "bridge_id": bridge_id,
        "sign_key_id": sign_key_id,
        "target_position": int(position),
        "rain_override": bool(mod.get("force")),
        "timezone": timezone,
        "home_id": home_id,
        "app_version": APP_VERSION,
    }
    payload={"app_type":"app_velux","app_version":APP_VERSION,
             "home":{"id":home_id,"timezone":timezone,"modules":[mod]}}
    data=post_json(SYNC_SETSTATE_URL,payload,timeout=25,token=token)
    body=data.get("body") if isinstance(data,dict) else None
    errors=body.get("errors") if isinstance(body,dict) else None
    if errors:
        raise VeluxError(f"signiertes setstate API-Fehler: {errors}; diag={diag}")
    if isinstance(data,dict):
        data["_loxberry_sign_diag"]=diag
    return data


def signed_home_scenario(token: str, home_id: str, gateway_id: str,
                         sign_key_id: str, hash_sign_key: str,
                         timezone: str="Europe/Zurich") -> dict[str, Any]:
    from signing import build_signed_scenario
    mod=build_signed_scenario(gateway_id,"home",sign_key_id,hash_sign_key)
    payload={"app_type":"app_velux","app_version":APP_VERSION,
             "home":{"id":home_id,"timezone":timezone,"modules":[mod]}}
    data=post_json(SYNC_SETSTATE_URL,payload,timeout=25,token=token)
    body=data.get("body") if isinstance(data,dict) else None
    errors=body.get("errors") if isinstance(body,dict) else None
    if errors:
        raise VeluxError(f"Automatisierung aktivieren API-Fehler: {errors}")
    return data


def set_window_mode(token: str, home_id: str, module_id: str, bridge_id: str,
                    mode: str, timezone: str="Europe/Zurich") -> dict[str, Any]:
    """Set VELUX window algorithm mode. Official app uses algo_available/manual."""
    payload={"app_type":"app_velux","app_version":APP_VERSION,
             "home":{"id":home_id,"timezone":timezone,
                     "modules":[{"id":module_id,"bridge":bridge_id,"mode":str(mode)}]}}
    data=post_json(SYNC_SETSTATE_URL,payload,timeout=25,token=token)
    body=data.get("body") if isinstance(data,dict) else None
    errors=body.get("errors") if isinstance(body,dict) else None
    if errors:
        raise VeluxError(f"Fenster-Automatik API-Fehler: {errors}")
    return data
