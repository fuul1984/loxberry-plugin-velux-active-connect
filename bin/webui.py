from __future__ import annotations
import html, json, os, subprocess, sys, time, urllib.parse
from pathlib import Path
from version import plugin_version
PLUGIN="veluxactive"; VERSION=plugin_version()
LBROOT=Path(os.environ.get("LBHOMEDIR","/opt/loxberry"))
CFG=Path(os.environ.get("LBPCONFIGDIR", str(LBROOT/f"config/plugins/{PLUGIN}")))
DATA=Path(os.environ.get("LBPDATADIR", str(LBROOT/f"data/plugins/{PLUGIN}")))
LOG=Path(os.environ.get("LBPLOGDIR", str(LBROOT/f"log/plugins/{PLUGIN}")))
BIN=Path(os.environ.get("LBPBINDIR", str(LBROOT/f"bin/plugins/{PLUGIN}")))
CFG.mkdir(parents=True,exist_ok=True); DATA.mkdir(parents=True,exist_ok=True); LOG.mkdir(parents=True,exist_ok=True)
config_file=CFG/"config.json"; state_file=DATA/"state.json"; run_file=DATA/"last_run.json"; scheduler_success_file=DATA/"scheduler_last_success.timestamp"; control_state_file=DATA/"control_state.json"; rx_state_file=DATA/"control_rx.json"; log_file=LOG/"veluxactive.log"; token_file=CFG/"tokens.json"; default_file=Path(os.environ.get("LBPTEMPLATEDIR", str(LBROOT/f"templates/plugins/{PLUGIN}")))/"default.json"
def load(p,d):
    try:return json.loads(p.read_text(encoding="utf-8"))
    except:return d
def esc(x): return html.escape(str(x),quote=True)
def fmt_ts(ts):
    try:return time.strftime("%d.%m.%Y %H:%M:%S",time.localtime(int(ts)))
    except:return "-"
def display_value(value, meta=None):
    meta=meta or {}
    if meta.get("unit")=="°C":
        try:
            n=float(value)
            if abs(n)>80: n/=10.0
            return f"{n:.1f}"
        except (TypeError,ValueError):
            pass
    if isinstance(value,bool): return "1" if value else "0"
    return value
def parse_form():
    method=os.environ.get("REQUEST_METHOD","GET").upper(); raw=""
    if method=="POST":
        try:length=int(os.environ.get("CONTENT_LENGTH","0") or 0)
        except ValueError:length=0
        raw=sys.stdin.read(length) if length else ""
    else: raw=os.environ.get("QUERY_STRING","")
    parsed=urllib.parse.parse_qs(raw, keep_blank_values=True)
    return {k:(v[-1] if v else "") for k,v in parsed.items()}
def get_miniservers():
    try:
        r=subprocess.run([str(BIN/"loxberry_bridge.pl"),"list"],capture_output=True,text=True,timeout=10)
        if r.returncode != 0:return [], (r.stderr.strip() or "Miniserver-Abfrage fehlgeschlagen")
        raw=json.loads(r.stdout or "[]")
        if isinstance(raw,dict): raw=[raw]
        return (raw if isinstance(raw,list) else []), ""
    except Exception as e:return [], str(e)
def pick(d,*names,default=""):
    if not isinstance(d,dict): return default
    lower={str(k).lower():v for k,v in d.items()}
    for n in names:
        if n in d and d[n] not in (None,""): return d[n]
        if n.lower() in lower and lower[n.lower()] not in (None,""): return lower[n.lower()]
    return default

def save_cfg(cfg):
    config_file.write_text(json.dumps(cfg,indent=2,ensure_ascii=False),encoding="utf-8"); os.chmod(config_file,0o600)

def run_worker(force_login=False):
    env=os.environ.copy(); env.update({"LBPCONFIGDIR":str(CFG),"LBPDATADIR":str(DATA),"LBPLOGDIR":str(LOG),"LBPBINDIR":str(BIN),"LBPTEMPLATEDIR":str(default_file.parent),"LBPCONFIG":str(CFG),"LBPDATA":str(DATA),"LBPLOG":str(LOG)})
    cmd=[sys.executable,str(BIN/"worker.py"),"--force"] + (["--force-login"] if force_login else [])
    return subprocess.run(cmd,capture_output=True,text=True,timeout=90,env=env)


def run_control(device, command, value="1"):
    env=os.environ.copy()
    env.update({
        "LBPCONFIGDIR":str(CFG),
        "LBPDATADIR":str(DATA),
        "LBPLOGDIR":str(LOG),
        "LBPBINDIR":str(BIN),
    })
    cmd=[sys.executable,str(BIN/"control_cli.py"),"--device",str(device),"--command",str(command),"--value",str(value)]
    return subprocess.run(cmd,capture_output=True,text=True,timeout=45,env=env)



def run_export():
    env=os.environ.copy()
    env.update({"LBPCONFIGDIR":str(CFG),"LBPDATADIR":str(DATA),"LBPLOGDIR":str(LOG)})
    return subprocess.run([sys.executable,str(BIN/"loxone_export.py")],capture_output=True,text=True,timeout=20,env=env)



def udp_selftest():
    import socket as _socket
    c=cfg.get("control",{}) if isinstance(cfg.get("control"),dict) else {}
    port=int(c.get("udp_listen_port",7001))
    prefix=str(c.get("command_prefix","velux.cmd") or "velux.cmd").rstrip(".")
    msg=f"{prefix}.__selftest__.ping=1"
    sock=_socket.socket(_socket.AF_INET,_socket.SOCK_DGRAM)
    sock.sendto(msg.encode("utf-8"),("127.0.0.1",port))
    sock.close()
    time.sleep(.25)
    return msg



def loxberry_ip():
    for key in ("loxberry_ip","local_ip"):
        value=str(cfg.get(key,"") or "").strip()
        if value:
            return value
    try:
        import socket
        sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8",80))
        ip=sock.getsockname()[0]
        sock.close()
        if ip and not ip.startswith("127."):
            return ip
    except Exception:
        pass
    return "LOXBERRY-IP"


form=parse_form(); cfg=load(config_file,load(default_file,{})); state=load(state_file,{})
page=form.get("page","status") or "status"; action=form.get("action",""); message=""; message_cls=""
miniservers,miniserver_error=get_miniservers()

def selected_sender_ips():
    # If the LoxBerry Miniserver list is temporarily unavailable, preserve the
    # existing allow-list instead of silently clearing it while saving settings.
    if miniserver_error or not miniservers:
        return None
    ips=[]
    for i,ms in enumerate(miniservers,1):
        no=int(pick(ms,"_msno",default=i) or i)
        ip=str(pick(ms,"IPAddress","ipaddress","IP","ip",default="") or "").strip()
        if ip and f"control_sender_{no}" in form:
            ips.append(ip)
    return sorted(set(ips))

def save_main_settings():
    global cfg
    old_pw=cfg.get("password","")
    cfg["email"]=form.get("email",cfg.get("email","")).strip()
    pw=form.get("password","")
    if pw: cfg["password"]=pw
    cfg["poll_interval_minutes"]=max(1,int(form.get("poll_interval_minutes",cfg.get("poll_interval_minutes",5))))
    cfg["udp_enabled"]="udp_enabled" in form
    cfg["miniserver_no"]=max(1,int(form.get("miniserver_no",cfg.get("miniserver_no",1))))
    cfg["udp_port"]=int(form.get("udp_port",cfg.get("udp_port",7000)))
    cfg["udp_prefix"]=form.get("udp_prefix",cfg.get("udp_prefix","velux")).strip() or "velux"
    cfg["heartbeat_enabled"]="heartbeat_enabled" in form
    cfg["udp_heartbeat_key"]=form.get("udp_heartbeat_key",cfg.get("udp_heartbeat_key","heartbeat")).strip() or "heartbeat"
    cfg["udp_auto_new"]="udp_auto_new" in form
    mode=form.get("udp_send_mode",cfg.get("udp_send_mode","always"))
    cfg["udp_send_mode"]=mode if mode in ("always","changed") else "always"
    c=cfg.get("control",{}) if isinstance(cfg.get("control",{}),dict) else {}
    c["enabled"]="control_enabled" in form
    c["udp_listen_port"]=int(form.get("control_udp_listen_port",c.get("udp_listen_port",7001)))
    c["command_prefix"]=form.get("control_command_prefix",c.get("command_prefix","velux.cmd")).strip() or "velux.cmd"
    sender_ips=selected_sender_ips()
    if sender_ips is not None:
        c["allowed_senders"]=sender_ips
    cfg["control"]=c
    save_cfg(cfg)
    try: (DATA/"udp_last_sent.json").unlink()
    except FileNotFoundError: pass
    try: subprocess.run([str(BIN/"control_watchdog.sh")],capture_output=True,text=True,timeout=10)
    except Exception: pass
    if pw and pw != old_pw:
        try: token_file.unlink()
        except FileNotFoundError: pass

def save_udp_settings():
    global cfg
    # IMPORTANT:
    # The "UDP Messages" page contains only the per-value selection/name fields.
    # Do NOT modify general UDP settings here (udp_enabled, heartbeat_enabled,
    # udp_auto_new, miniserver, ports, prefix, send mode). Those belong only
    # to the Settings page. Previously the missing checkboxes were interpreted
    # as False and silently disabled UDP/Heartbeat when saving message choices.
    rules=cfg.get("udp_messages",{}) if isinstance(cfg.get("udp_messages",{}),dict) else {}
    try: count=int(form.get("udp_count","0"))
    except: count=0
    for i in range(count):
        key=form.get(f"udp_key_{i}","")
        if not key: continue
        rules[key]={"enabled":f"udp_en_{i}" in form,"name":form.get(f"udp_name_{i}",key).strip() or key}
    cfg["udp_messages"]=rules; save_cfg(cfg)
    # A change of UDP configuration should perform a fresh initial sync when
    # changed-only mode is active.
    try: (DATA/"udp_last_sent.json").unlink()
    except FileNotFoundError: pass

def save_control_settings():
    global cfg
    c=cfg.get("control",{}) if isinstance(cfg.get("control",{}),dict) else {}
    c["enabled"]="control_enabled" in form
    c["udp_listen_port"]=int(form.get("control_udp_listen_port",c.get("udp_listen_port",7001)))
    c["command_prefix"]=form.get("control_command_prefix",c.get("command_prefix","velux.cmd")).strip() or "velux.cmd"
    sender_ips=selected_sender_ips()
    if sender_ips is not None:
        c["allowed_senders"]=sender_ips
    cfg["control"]=c; save_cfg(cfg)

try:
    if action=="save_settings": save_main_settings(); message="Einstellungen gespeichert."; message_cls="okbox"; page="settings"
    elif action=="save_udp": save_udp_settings(); message="UDP-Messages gespeichert."; message_cls="okbox"; page="udp"
    elif action in ("udp_all_on","udp_all_off"):
        vals=state.get("values",{}) if isinstance(state.get("values",{}),dict) else {}
        rules=cfg.get("udp_messages",{}) if isinstance(cfg.get("udp_messages",{}),dict) else {}
        enabled=(action=="udp_all_on")
        for key in vals:
            old=rules.get(key,{}) if isinstance(rules.get(key,{}),dict) else {}
            rules[key]={"enabled":enabled,"name":old.get("name") or key}
        cfg["udp_messages"]=rules; save_cfg(cfg)
        try: (DATA/"udp_last_sent.json").unlink()
        except FileNotFoundError: pass
        message=("Alle erkannten UDP-Werte aktiviert." if enabled else "Alle erkannten UDP-Werte deaktiviert.")
        message_cls="okbox"; page="udp"
    elif action=="save_control":
        save_control_settings()
        try:
            subprocess.run([str(BIN/"control_watchdog.sh")],capture_output=True,text=True,timeout=10)
        except Exception:
            pass
        message="Steuerungseinstellungen gespeichert."; message_cls="okbox"; page="control"
    elif action=="toggle_plugin":
        cfg["plugin_enabled"]=not bool(cfg.get("plugin_enabled",True))
        save_cfg(cfg)
        try:
            subprocess.run([str(BIN/"control_watchdog.sh")],capture_output=True,text=True,timeout=10)
        except Exception:
            pass
        message=("Plugin aktiviert." if cfg["plugin_enabled"] else "Plugin deaktiviert.")
        message_cls="okbox"; page="status"
    elif action=="udp_selftest":
        try:
            sent=udp_selftest()
            rx_state=load(rx_state_file,{})
            if rx_state.get("text")==sent:
                message="UDP-Listener Selbsttest OK: Paket wurde lokal empfangen."; message_cls="okbox"
            else:
                message="UDP-Listener Selbsttest fehlgeschlagen: Listener/Port empfängt das Testpaket nicht."; message_cls="badbox"
        except Exception as e:
            message=f"UDP-Listener Selbsttest fehlgeschlagen: {e}"; message_cls="badbox"
        page="control"
    elif action=="pair_gateway":
        host=form.get("gateway_ip","").strip()
        gateway_id=form.get("gateway_id","").strip()
        if not host:
            message="Gateway-IP fehlt."; message_cls="badbox"; page="settings"
        else:
            env=os.environ.copy(); env.update({"LBPCONFIGDIR":str(CFG),"LBPDATADIR":str(DATA),"LBPLOGDIR":str(LOG)})
            cmd=[sys.executable,str(BIN/"gateway_pair.py"),"--host",host]
            if gateway_id: cmd+=["--gateway-id",gateway_id]
            r=subprocess.run(cmd,capture_output=True,text=True,timeout=60,env=env)
            cfg=load(config_file,cfg)
            if r.returncode==0:
                message="Gateway erfolgreich gekoppelt. Signierschlüssel wurde gespeichert."; message_cls="okbox"
            else:
                try: err=json.loads(r.stdout.strip()).get("error")
                except: err=None
                message="Gateway-Kopplung fehlgeschlagen: "+(err or r.stderr.strip() or r.stdout.strip() or f"Code {r.returncode}"); message_cls="badbox"
            page="settings"
    elif action=="control_automation":
        r=run_control("velux_active","automation","1")
        control_state=load(control_state_file,{})
        if r.returncode==0:
            message="VELUX ACTIVE Automatisierung aktiviert."
            message_cls="okbox"
        else:
            # Prefer the subprocess error. control_state may still contain an older command
            # if control_cli failed before it could write a new state.
            detail=(r.stderr.strip() or r.stdout.strip() or control_state.get("result") or f"Code {r.returncode}")
            message="Automatisierung konnte nicht aktiviert werden: "+detail
            message_cls="badbox"
        page="control"
    elif action in ("control_open","control_close","control_stop","control_position"):
        device=form.get("control_device","").strip()
        cmd={"control_open":"open","control_close":"close","control_stop":"stop","control_position":"position"}[action]
        value=form.get("control_value","1") if cmd=="position" else "1"
        r=run_control(device,cmd,value)
        control_state=load(control_state_file,{})
        rx_state=load(rx_state_file,{})
        if r.returncode==0:
            message=f"Steuerbefehl erfolgreich: {control_state.get('device',device)} – {cmd}={value} – {control_state.get('result','OK')}"
            message_cls="okbox"
        else:
            message="Steuerbefehl fehlgeschlagen: "+(control_state.get("result") or r.stderr.strip() or r.stdout.strip() or f"Code {r.returncode}")
            message_cls="badbox"
        page="control"
    elif action in ("fetch","relogin"):
        r=run_worker(action=="relogin"); state=load(state_file,{})
        if r.returncode==0: message=f"VELUX Abruf erfolgreich: {len(state.get('devices',[]))} Gerät(e), {len(state.get('values',{}))} Wert(e), UDP={state.get('udp_messages',0)}."; message_cls="okbox"
        else: message="VELUX Abruf fehlgeschlagen: "+(state.get("error") or r.stderr.strip() or f"Worker Code {r.returncode}"); message_cls="badbox"
        page="status"
except Exception as e:
    message=f"Aktion fehlgeschlagen: {type(e).__name__}: {e}"; message_cls="badbox"

state=load(state_file,{})
run_state=load(run_file,{})
scheduler_last_success=0
try:
    _raw=scheduler_success_file.read_text(encoding="utf-8").strip()
    scheduler_last_success=int(_raw) if _raw.isdigit() else 0
except Exception:
    scheduler_last_success=0
control_state=load(control_state_file,{})
rx_state=load(rx_state_file,{})
try: log_lines=log_file.read_text(encoding="utf-8",errors="replace").splitlines()[-250:]
except: log_lines=[]
def checked(v):return "checked" if v else ""
def nav(name,label):return f'<a class="nav {"active" if page==name else ""}" href="?page={name}">{label}</a>'

print(f'''<style>
*{{box-sizing:border-box}}
.wrap{{max-width:1180px;margin:18px auto;padding:0 12px;color:#222}}
.hero{{background:#ef7d00!important;background-image:none!important;color:#fff!important;padding:18px 22px;border-radius:10px;display:flex;align-items:center;gap:16px;box-shadow:none!important;filter:none!important}}
.hero img{{width:54px;height:54px;flex:0 0 auto}}
.hero,.hero *,h1,h2,h3,h4,h5,h6{{text-shadow:none!important;filter:none!important}}
.hero h1{{margin:0;color:#fff!important;font-size:28px;line-height:1.2}}
.hero h1 small{{color:#fff!important;font-size:.58em;font-weight:600;white-space:nowrap}}
.tabs{{display:flex;gap:7px;flex-wrap:wrap;margin:14px 0}}
.nav,.nav:link,.nav:visited{{padding:10px 15px;background:#e9edf0!important;background-image:none!important;color:#223!important;text-decoration:none!important;border:1px solid #c5ccd2!important;border-radius:7px;font-weight:700;text-shadow:none!important;box-shadow:none!important;filter:none!important}}
.nav:hover,.nav:focus{{background:#dfe5e9!important;color:#17212a!important}}
.nav.active,.nav.active:link,.nav.active:visited,.nav.active:hover,.nav.active:focus,.nav.active:active{{background:#34495e!important;background-image:none!important;color:#fff!important;border-color:#263746!important;text-shadow:none!important;box-shadow:none!important;filter:none!important;outline:none!important}}
.card{{background:#fff;color:#222;padding:18px;border-radius:10px;margin:12px 0;box-shadow:0 1px 7px #0001;overflow:hidden}}
.card h2{{margin-top:0;font-size:21px}}
.section-head{{display:flex;align-items:flex-start;justify-content:space-between;gap:12px;flex-wrap:wrap;margin-bottom:12px}}
.section-head h2{{margin:0}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:14px}}
.field{{min-width:0}}
label{{display:block;font-weight:700;margin:0 0 5px}}
input[type=text],input[type=password],input[type=number],select{{width:100%;max-width:100%;padding:10px;border:1px solid #ccd2d8;border-radius:6px;background:#fff!important;color:#222!important;min-height:42px}}
input[type=checkbox]{{width:20px;height:20px;flex:0 0 20px}}
.btn,.btn:link,.btn:visited{{appearance:none!important;-webkit-appearance:none!important;background-image:none!important;border:1px solid transparent!important;border-radius:7px!important;padding:10px 16px!important;font-weight:700!important;cursor:pointer;margin:3px;line-height:1.25;text-decoration:none!important;text-shadow:none!important;box-shadow:none!important;filter:none!important;min-height:42px}}
.btn.primary{{background:#ef7d00!important;color:#fff!important;border-color:#c96700!important}}
.btn.secondary{{background:#34495e!important;color:#fff!important;border-color:#263746!important}}
.btn.ghost{{background:#e9edf0!important;color:#1f2d38!important;border-color:#bfc7ce!important}}
.btn.up{{background:#16833b!important;color:#fff!important;border-color:#10642d!important}}
.btn.stop{{background:#b77900!important;color:#fff!important;border-color:#8f5e00!important}}
.btn.down{{background:#c0392b!important;color:#fff!important;border-color:#922b21!important}}
.btn:hover{{opacity:.92}} .btn:focus{{outline:3px solid rgba(52,73,94,.25)!important;outline-offset:2px}} .btn:active,.btn.active{{transform:none!important}} .btn:disabled{{opacity:.55;cursor:not-allowed}}
.ok{{color:#16833b}}.bad{{color:#c0392b}}
.okbox{{background:#eaf7ee!important;color:#183b23!important;border-left:5px solid #16833b;padding:12px}}
.badbox{{background:#fdeeee!important;color:#4d1712!important;border-left:5px solid #c0392b;padding:12px}}
.muted{{color:#667;font-size:13px}} .badge{{display:inline-block;padding:3px 8px;border-radius:15px;background:#eef1f3;color:#27333d;font-size:12px}}
.statusbar{{display:flex;gap:8px;flex-wrap:wrap;margin:10px 0 14px}}
.statuspill{{display:inline-flex;align-items:center;gap:6px;padding:7px 10px;border-radius:999px;background:#eef1f3;color:#27333d;font-weight:700;font-size:13px}}
.statuspill.on{{background:#eaf7ee;color:#17612e}} .statuspill.off{{background:#f3f3f3;color:#666}} .statuspill.warn{{background:#fff4dd;color:#805500}}
.switchline{{display:flex;gap:9px;align-items:flex-start;font-weight:700;margin:7px 0}}
.setting-row{{display:flex;gap:14px;align-items:center;justify-content:space-between;padding:11px 0;border-bottom:1px solid #eef0f2}} .setting-row:last-child{{border-bottom:0}} .setting-main{{min-width:0;flex:1}} .setting-main b{{display:block}} .setting-control{{min-width:190px;max-width:320px;flex:0 0 38%}} .setting-control input,.setting-control select{{margin:0!important}}
.compact-grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}} .subcard{{border:1px solid #e4e8eb;border-radius:8px;padding:12px;background:#fafbfc}} .subcard h3{{margin:0 0 8px;font-size:15px;text-shadow:none!important}} details.advanced{{margin-top:12px;border-top:1px solid #e8ebed;padding-top:10px}} details.advanced summary{{cursor:pointer;font-weight:700;color:#34495e}}
.help{{margin-top:5px;color:#667;font-size:13px;line-height:1.35}}
.udpname{{min-width:0}} .ctrlrow{{display:flex;gap:7px;align-items:center;flex-wrap:wrap}} .ctrlrow input[type=number]{{width:90px}}
table.responsive{{width:100%;border-collapse:collapse;table-layout:fixed}} table.responsive th,table.responsive td{{padding:9px;border-bottom:1px solid #eee;text-align:left;vertical-align:middle;overflow-wrap:anywhere}}
table.responsive th:first-child{{width:90px}} table.responsive code{{overflow-wrap:anywhere;word-break:break-word}}
.udp-table{{table-layout:auto!important}}
.udp-table th:nth-child(1),.udp-table td:nth-child(1){{width:84px!important;min-width:84px!important;max-width:84px!important}}
.udp-table th:nth-child(2),.udp-table td:nth-child(2){{width:34%}}
.udp-table th:nth-child(3),.udp-table td:nth-child(3){{width:110px;min-width:90px}}
.udp-table th:nth-child(4),.udp-table td:nth-child(4){{width:auto}}
.udp-table td{{vertical-align:middle}}
.udp-table .udpname{{width:100%;box-sizing:border-box;min-width:180px}}
.udp-table th:first-child,.udp-table td:first-child{{text-align:center!important}} .udp-check{{display:flex!important;align-items:center!important;justify-content:center!important;width:100%!important;min-height:28px!important}} .udp-checkbox{{appearance:auto!important;-webkit-appearance:checkbox!important;display:inline-block!important;position:static!important;opacity:1!important;visibility:visible!important;width:20px!important;height:20px!important;min-width:20px!important;min-height:20px!important;margin:0!important;padding:0!important;transform:none!important;clip:auto!important;accent-color:auto!important;cursor:pointer!important}}
.udp-key{{display:block;margin-top:4px;color:#66727c;font-size:12px;word-break:break-all}}
.udp-current{{white-space:nowrap}}

.current-values-table{{table-layout:auto!important}}
.current-values-table th:nth-child(1),.current-values-table td:nth-child(1){{width:42%!important}}
.current-values-table th:nth-child(2),.current-values-table td:nth-child(2){{width:18%!important;min-width:120px!important;white-space:nowrap!important}}
.current-values-table th:nth-child(3),.current-values-table td:nth-child(3){{width:40%!important}}
.current-values-table td{{vertical-align:middle!important}}
.current-values-table td:nth-child(1) b{{display:block;line-height:1.3}}
.current-values-table code{{display:block;font-size:12px;line-height:1.35;color:#66727c;word-break:break-word;overflow-wrap:anywhere}}

code{{font-size:12px;overflow-wrap:anywhere}} pre{{white-space:pre-wrap;word-break:break-word;background:#111;color:#eee;padding:12px;border-radius:7px;max-height:520px;overflow:auto;font-size:12px;line-height:1.45}}
.actions{{display:flex;gap:8px;flex-wrap:wrap;align-items:center}}
@media(max-width:700px){{
 .wrap{{margin:8px auto;padding:0 7px}} .hero{{padding:13px 14px;gap:10px;border-radius:8px}} .hero img{{width:42px;height:42px}} .hero h1{{font-size:20px}} .hero h1 small{{display:block;font-size:12px;margin-top:3px}} .hero div>div{{font-size:12px}}
 .tabs{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:6px;margin:9px 0}} .nav,.nav:link,.nav:visited{{padding:10px 8px;text-align:center;font-size:13px}}
 .card{{padding:13px;margin:9px 0;border-radius:8px}} .card h2{{font-size:18px}} .grid,.compact-grid{{grid-template-columns:1fr;gap:11px}} .section-head{{display:block}} .setting-row{{display:block}} .setting-control{{min-width:0;max-width:none;margin-top:8px}}
 .actions{{display:grid;grid-template-columns:1fr;gap:6px}} .actions .btn,.card>form>.btn{{width:100%;margin:0}} .btn{{margin:2px 0}}
 table.responsive,table.responsive tbody,table.responsive tr,table.responsive td{{display:block;width:100%}} table.responsive thead{{display:none}} table.responsive tr{{border:1px solid #e1e5e8;border-radius:8px;margin:10px 0;padding:4px 10px;background:#fff}} table.responsive td{{border:0;border-bottom:1px solid #f0f1f2;padding:8px 0;display:grid;grid-template-columns:minmax(92px,34%) 1fr;gap:8px;align-items:start}} table.responsive td:last-child{{border-bottom:0}} table.responsive td:before{{content:attr(data-label);font-weight:700;color:#56616b}}
 .udp-table{{table-layout:auto!important}} .udp-table .udpname{{width:100%!important;min-width:0}} .udp-current{{white-space:normal}} .udpname{{width:100%!important}} .ctrlrow{{display:grid;grid-template-columns:repeat(3,1fr);width:100%}} .ctrlrow input[type=number]{{width:100%;grid-column:1/-1}} .ctrlrow .secondary{{grid-column:1/-1}} .statusbar{{gap:5px}} .statuspill{{font-size:12px;padding:6px 8px}} pre{{max-height:65vh;font-size:11px}}
}}
@media(max-width:390px){{.tabs{{grid-template-columns:1fr}} .hero h1{{font-size:18px}}}}

 @media(max-width:700px){{
   .udp-table,.udp-table tbody{{display:block!important;width:100%!important}}
   .udp-table thead{{display:none!important}}
   .udp-table tr{{display:grid!important;grid-template-columns:48px minmax(0,1fr)!important;gap:8px 10px!important;border:1px solid #e1e5e8!important;border-radius:10px!important;margin:10px 0!important;padding:12px!important;background:#fff!important;width:100%!important;box-sizing:border-box!important}}
   .udp-table td{{display:block!important;width:auto!important;min-width:0!important;max-width:none!important;border:0!important;padding:0!important;text-align:left!important}}
   .udp-table td:before{{display:none!important;content:none!important}}
   .udp-table td:nth-child(1){{grid-column:1!important;grid-row:1!important;display:flex!important;align-items:flex-start!important;justify-content:center!important;padding-top:2px!important}}
   .udp-table td:nth-child(2){{grid-column:2!important;grid-row:1!important}}
   .udp-table td:nth-child(3){{grid-column:1 / -1!important;grid-row:2!important;padding-top:8px!important;border-top:1px solid #f0f1f2!important}}
   .udp-table td:nth-child(3):before{{display:inline!important;content:"Aktuell: "!important;font-weight:700!important;color:#56616b!important}}
   .udp-table td:nth-child(4){{grid-column:1 / -1!important;grid-row:3!important;padding-top:8px!important}}
   .udp-table td:nth-child(4):before{{display:block!important;content:"UDP Message"!important;font-weight:700!important;color:#56616b!important;margin-bottom:6px!important}}
   .udp-table .udpname{{width:100%!important;min-width:0!important;font-size:16px!important}}
   .udp-table .udp-key{{font-size:11px!important;line-height:1.3!important}}
   .udp-table .udp-checkbox{{width:22px!important;height:22px!important;min-width:22px!important;min-height:22px!important}}
 }}


 @media(max-width:700px){{
   .current-values-table td{{width:100%!important;min-width:0!important;max-width:none!important;white-space:normal!important}}
   .current-values-table td:nth-child(2){{font-size:16px!important;font-weight:700!important}}
   .current-values-table code{{font-size:11px!important}}
 }}


 @media(max-width:700px){{
   .current-values-table,.current-values-table tbody{{display:block!important;width:100%!important}}
   .current-values-table thead{{display:none!important}}
   .current-values-table tr{{display:block!important;border:1px solid #e1e5e8!important;border-radius:10px!important;margin:10px 0!important;padding:12px!important;background:#fff!important;width:100%!important;box-sizing:border-box!important}}
   .current-values-table td{{display:block!important;width:100%!important;min-width:0!important;max-width:none!important;border:0!important;padding:0!important;text-align:left!important;white-space:normal!important}}
   .current-values-table td:before{{display:none!important;content:none!important}}
   .current-values-table td:nth-child(1){{font-size:16px!important;font-weight:700!important;line-height:1.35!important}}
   .current-values-table td:nth-child(2){{margin-top:8px!important;padding:8px 0!important;border-top:1px solid #f0f1f2!important;font-size:19px!important;font-weight:700!important;line-height:1.25!important}}
   .current-values-table td:nth-child(2):before{{display:inline!important;content:"Aktuell: "!important;font-size:13px!important;font-weight:700!important;color:#66727c!important}}
   .current-values-table td:nth-child(3){{margin-top:2px!important;padding-top:7px!important}}
   .current-values-table td:nth-child(3):before{{display:block!important;content:"VELUX Schlüssel"!important;font-size:12px!important;font-weight:700!important;color:#66727c!important;margin-bottom:3px!important}}
   .current-values-table code{{font-size:11px!important;line-height:1.3!important;word-break:break-all!important;overflow-wrap:anywhere!important;color:#66727c!important}}
 }}

</style>
<div class="wrap"><div class="hero"><img src="icon_128.png" alt="VELUX Active Connect"><div><h1>VELUX Active Connect <small>{esc(VERSION)}</small></h1><div>VELUX ACTIVE / App Control → LoxBerry → Loxone</div></div></div>
<div class="tabs">{nav('status','Status')}{nav('settings','Einstellungen')}{nav('udp','UDP Messages')}{nav('control','Steuerung')}{nav('log','Log')}</div>''')
if message: print(f'<div class="card {message_cls}"><b>{esc(message)}</b></div>')

if page=="settings":
    c=cfg.get("control",{}) if isinstance(cfg.get("control",{}),dict) else {}
    signing=cfg.get("signing",{}) if isinstance(cfg.get("signing",{}),dict) else {}
    gateways=[d for d in state.get("devices",[]) if str(d.get("type","")).upper()=="NXG"]
    print('<form method="post"><input type="hidden" name="page" value="settings">')
    print('<div class="card"><div class="section-head"><div><h2>VELUX Konto</h2><div class="muted">Anmeldung an VELUX ACTIVE / App Control. Das Passwortfeld bleibt beim Speichern unverändert, wenn es leer ist.</div></div></div><div class="grid">')
    print(f'<div class="field"><label>E-Mail</label><input type="text" name="email" value="{esc(cfg.get("email",""))}" autocomplete="username"></div>')
    print('<div class="field"><label>Passwort</label><input type="password" name="password" placeholder="Gespeichertes Passwort unverändert lassen" autocomplete="current-password"></div></div></div>')
    print('<div class="card"><h2>Abruf & Plugin</h2><div class="grid">')
    print(f'<div class="field"><label>Abrufintervall</label><input type="number" min="1" name="poll_interval_minutes" value="{esc(cfg.get("poll_interval_minutes",5))}"><div class="help">Intervall in Minuten. Der Scheduler prüft jede Minute, ob ein Abruf fällig ist.</div></div>')
    print(f'<div class="field"><label>Pluginstatus</label><div class="statuspill {"on" if cfg.get("plugin_enabled",True) else "off"}">{"Aktiv" if cfg.get("plugin_enabled",True) else "Inaktiv"}</div><div class="help">Aktivieren/Deaktivieren erfolgt auf der Statusseite.</div></div></div></div>')
    print('<div class="card"><div class="section-head"><div><h2>VELUX → Loxone · UDP Statuswerte</h2><div class="muted">Nur die wichtigsten Einstellungen direkt sichtbar. Die Auswahl einzelner Werte erfolgt unter „UDP Messages“.</div></div></div>')
    print('<div class="compact-grid">')
    print('<div class="subcard"><h3>Versand</h3>')
    print(f'<label class="switchline"><input type="checkbox" name="udp_enabled" {checked(cfg.get("udp_enabled"))}> UDP-Ausgabe aktiv</label>')
    print(f'<div class="field"><label>Sendeverhalten</label><select name="udp_send_mode"><option value="always" {"selected" if cfg.get("udp_send_mode","always")=="always" else ""}>Alle ausgewählten Werte</option><option value="changed" {"selected" if cfg.get("udp_send_mode")=="changed" else ""}>Nur Änderungen</option></select></div>')
    print('</div>')
    print('<div class="subcard"><h3>Ziel Loxone</h3><div class="field"><label>Miniserver</label><select name="miniserver_no">')
    selected=int(cfg.get("miniserver_no",1) or 1)
    if miniservers:
        for i,ms in enumerate(miniservers,1):
            no=int(pick(ms,"_msno",default=i) or i); name=pick(ms,"Name","name",default=f"Miniserver {no}"); ip=pick(ms,"IPAddress","ipaddress","IP","ip",default=""); sel=" selected" if no==selected else ""
            print(f'<option value="{no}"{sel}>{esc(name)}{esc(" — "+ip if ip else "")}</option>')
    else: print('<option value="1">Kein Miniserver gefunden</option>')
    print('</select></div>')
    print(f'<div class="field"><label>UDP-Port</label><input type="number" name="udp_port" min="1" max="65535" value="{esc(cfg.get("udp_port",7000))}"></div></div></div>')
    print('<details class="advanced"><summary>Erweiterte UDP-Einstellungen</summary><div class="compact-grid" style="margin-top:10px">')
    print(f'<div class="field"><label>Status-Präfix</label><input type="text" name="udp_prefix" value="{esc(cfg.get("udp_prefix","velux"))}"><div class="help">Beispiel: velux.module.dachfenster_bad.position</div></div>')
    print(f'<div class="field"><label class="switchline"><input type="checkbox" name="heartbeat_enabled" {checked(cfg.get("heartbeat_enabled",True))}> Heartbeat senden</label><input type="text" name="udp_heartbeat_key" value="{esc(cfg.get("udp_heartbeat_key","heartbeat"))}" aria-label="Heartbeat-Name"><div class="help">Name des Heartbeat-Werts.</div></div>')
    print(f'<div class="field"><label class="switchline"><input type="checkbox" name="udp_auto_new" {checked(cfg.get("udp_auto_new",True))}> Neue erkannte Werte automatisch aktivieren</label><div class="help">Kann anschließend unter „UDP Messages“ individuell angepasst werden.</div></div>')
    print('</div></details><div class="help" style="margin-top:10px">Welche Werte gesendet werden, stellst du übersichtlich auf der Seite <b>UDP Messages</b> ein.</div></div>')
    print('<div class="card"><h2>Loxone → VELUX · UDP Steuerung</h2><div class="grid">')
    print(f'<div class="field"><label class="switchline"><input type="checkbox" name="control_enabled" {checked(c.get("enabled",False))}> UDP-Steuerung aktiv</label><div class="help">Startet den überwachten Listener für Loxone-Befehle.</div></div>')
    print(f'<div class="field"><label>UDP-Empfangsport</label><input type="number" min="1" max="65535" name="control_udp_listen_port" value="{esc(c.get("udp_listen_port",7001))}"></div>')
    print(f'<div class="field"><label>Befehls-Präfix</label><input type="text" name="control_command_prefix" value="{esc(c.get("command_prefix","velux.cmd"))}"><div class="help">Standard: velux.cmd</div></div></div>')
    allowed=set(str(x) for x in c.get("allowed_senders",[]) if str(x))
    print('<h3>Erlaubte Absender</h3>')
    if miniservers:
        for i,ms in enumerate(miniservers,1):
            no=int(pick(ms,"_msno",default=i) or i); name=pick(ms,"Name","name",default=f"Miniserver {no}"); ip=str(pick(ms,"IPAddress","ipaddress","IP","ip",default="") or "").strip()
            if ip: print(f'<label class="switchline"><input type="checkbox" name="control_sender_{no}" {checked(ip in allowed)}> <span>{esc(name)}<br><span class="muted">{esc(ip)}</span></span></label>')
    else:
        detail=(" – "+esc(miniserver_error)) if miniserver_error else ""
        print(f'<div class="badbox"><b>Keine Miniserver gefunden{detail}.</b><br>Vorhandene erlaubte Absender bleiben beim Speichern unverändert.</div>')
    print('<div class="help">Ohne ausgewählten Absender werden Netzwerk-Steuerbefehle abgewiesen. Der lokale Selbsttest bleibt möglich.</div></div>')
    print('<div class="card"><h2>VELUX Gateway Kopplung</h2>')
    try:
        dep=subprocess.run([sys.executable,"-c","import cryptography; print(cryptography.__version__)"],capture_output=True,text=True,timeout=5)
        crypto_ok=dep.returncode==0
        print(f'<div class="statusbar"><span class="statuspill {"on" if crypto_ok else "off"}">Kryptografie: {"bereit" if crypto_ok else "fehlt"}</span><span class="statuspill {"on" if signing.get("sign_key_id") and signing.get("hash_sign_key") else "off"}">Gateway: {"gekoppelt" if signing.get("sign_key_id") and signing.get("hash_sign_key") else "nicht gekoppelt"}</span></div>')
    except Exception:
        print('<div class="statuspill off">Kryptografie: Prüfung fehlgeschlagen</div>')
    if signing.get("sign_key_id") and signing.get("hash_sign_key"):
        print(f'<p><b>Gateway-ID:</b> <code>{esc(signing.get("gateway_id",""))}</code><br><b>Gateway-IP:</b> {esc(signing.get("gateway_ip",""))}<br><b>Gekoppelt:</b> {esc(fmt_ts(signing.get("paired_at")))}</p>')
    print('<div class="grid">')
    print(f'<div class="field"><label>Gateway-IP</label><input type="text" name="gateway_ip" value="{esc(signing.get("gateway_ip",""))}" placeholder="192.168.1.x"></div>')
    print('<div class="field"><label>Gateway</label><select name="gateway_id">')
    if gateways:
        for g in gateways:
            sel=' selected' if g.get("id")==signing.get("gateway_id") else ''
            print(f'<option value="{esc(g.get("id"))}"{sel}>{esc(g.get("name"))} – {esc(g.get("id"))}</option>')
    else: print('<option value="">Kein NXG-Gateway erkannt</option>')
    print('</select></div></div><div class="help">Für die Kopplung muss TCP-Port 25050 zum Gateway erreichbar sein.</div>')
    print('<div class="actions" style="margin-top:12px"><button class="btn secondary" name="action" value="pair_gateway">Gateway koppeln</button></div></div>')
    print('<div class="card"><div class="actions"><button class="btn primary" name="action" value="save_settings">Einstellungen speichern</button></div></div></form>')
elif page=="udp":
    vals=state.get("values",{}) if isinstance(state.get("values",{}),dict) else {}
    meta=state.get("value_meta",{}) if isinstance(state.get("value_meta",{}),dict) else {}
    rules=cfg.get("udp_messages",{}) if isinstance(cfg.get("udp_messages",{}),dict) else {}
    enabled_count=0
    for key in vals:
        rule=rules.get(key,{})
        en=(rule.get("enabled",cfg.get("udp_auto_new",True)) if isinstance(rule,dict) else cfg.get("udp_auto_new",True))
        enabled_count += 1 if en else 0
    ms_label=f"Miniserver {cfg.get('miniserver_no',1)}"
    for i,ms in enumerate(miniservers,1):
        no=int(pick(ms,"_msno",default=i) or i)
        if no==int(cfg.get("miniserver_no",1) or 1):
            ms_label=str(pick(ms,"Name","name",default=ms_label)); ip=pick(ms,"IPAddress","ipaddress","IP","ip",default="")
            if ip: ms_label += f" · {ip}"
            break
    print('<div class="card"><div class="section-head"><div><h2>UDP Messages</h2><div class="muted">Auswahl der VELUX-Werte, die an Loxone gesendet werden.</div></div></div>')
    print('<div class="statusbar">')
    print(f'<span class="statuspill {"on" if cfg.get("udp_enabled") else "off"}">UDP: {"aktiv" if cfg.get("udp_enabled") else "inaktiv"}</span>')
    print(f'<span class="statuspill {"on" if cfg.get("heartbeat_enabled",True) else "off"}">Heartbeat: {"aktiv" if cfg.get("heartbeat_enabled",True) else "inaktiv"}</span>')
    print(f'<span class="statuspill">Modus: {"nur Änderungen" if cfg.get("udp_send_mode")=="changed" else "alle Werte"}</span>')
    print(f'<span class="statuspill">Aktiviert: {enabled_count}/{len(vals)}</span></div>')
    print(f'<p><b>Ziel:</b> {esc(ms_label)} · UDP {esc(cfg.get("udp_port",7000))}<br><b>Präfix:</b> <code>{esc(cfg.get("udp_prefix","velux"))}</code></p>')
    print('<div class="actions"><form method="post"><input type="hidden" name="page" value="udp"><button class="btn secondary" name="action" value="udp_all_on">Alle aktivieren</button><button class="btn ghost" name="action" value="udp_all_off">Alle deaktivieren</button></form></div><div class="help">Globale UDP-Einstellungen werden unter Einstellungen geändert.</div></div>')
    print('<form method="post"><input type="hidden" name="page" value="udp"><div class="card"><h2>Erkannte Werte</h2>')
    if vals:
        print('<table class="responsive udp-table"><thead><tr><th>Senden</th><th>VELUX Wert</th><th>Aktuell</th><th>UDP Message</th></tr></thead><tbody>')
        for i,key in enumerate(sorted(vals)):
            rule=rules.get(key,{}); en=rule.get("enabled",cfg.get("udp_auto_new",True)) if isinstance(rule,dict) else cfg.get("udp_auto_new",True); name=(rule.get("name") if isinstance(rule,dict) else None) or key; m=meta.get(key,{})
            print(f'<tr><td data-label="Senden"><div class="udp-check"><input class="udp-checkbox" type="checkbox" name="udp_en_{i}" {checked(en)} title="Diesen Wert an Loxone senden" aria-label="Diesen Wert an Loxone senden"></div><input type="hidden" name="udp_key_{i}" value="{esc(key)}"></td><td data-label="VELUX Wert"><b>{esc(m.get("label",key))}</b><code class="udp-key">{esc(key)}</code></td><td class="udp-current" data-label="Aktuell">{esc(display_value(vals[key],m))} {esc(m.get("unit",""))}</td><td data-label="UDP Message"><input class="udpname" type="text" name="udp_name_{i}" value="{esc(name)}"><div class="help"><code>{esc(cfg.get("udp_prefix","velux"))}.{esc(name)}</code></div></td></tr>')
        print(f'</tbody></table><input type="hidden" name="udp_count" value="{len(vals)}">')
    else: print('<div class="badbox">Noch keine Werte vorhanden. Bitte zuerst auf der Statusseite <b>VELUX Daten jetzt abrufen</b> ausführen.</div>')
    print('<div class="actions" style="margin-top:14px"><button class="btn primary" name="action" value="save_udp">UDP-Auswahl speichern</button></div></div></form>')
elif page=="control":
    c=cfg.get("control",{}) if isinstance(cfg.get("control",{}),dict) else {}
    print('<div class="card"><h2>Steuerung</h2><p>Hier kannst du die erkannten VELUX-Aktoren direkt bedienen. Die Loxone-Konfiguration findest du unter <b>Einstellungen</b>.</p></div>')
    paired=True
    print('<div class="card"><h2>VELUX ACTIVE Automatisierung</h2>')
    print('<p>Setzt den VELUX Fenstermodus wieder auf <code>algo_available</code> und gibt damit die automatische Lüftung wieder frei.</p>')
    if paired:
        print('<form method="post"><input type="hidden" name="page" value="control"><button class="btn primary" name="action" value="control_automation">Automatisierung aktivieren</button></form>')
        print('<p><b>Loxone UDP:</b> <code>velux.cmd.velux_active.automation=1</code></p>')
    else:
        print('<p><b>Hinweis:</b> Dieser Automatik-Befehl benötigt keine Signatur.</p>')
    print('</div>')
    c=cfg.get("control",{}) if isinstance(cfg.get("control",{}),dict) else {}
    pidfile=DATA/"control_listener.pid"
    listener_running=False; listener_pid=""
    try:
        listener_pid=pidfile.read_text().strip()
        if listener_pid:
            os.kill(int(listener_pid),0); listener_running=True
    except Exception:
        listener_running=False
    print('<div class="card"><h2>UDP Empfangsdiagnose</h2>')
    print(f'<p><b>Listener:</b> {"läuft" if listener_running else "NICHT aktiv"} {("· PID "+listener_pid) if listener_pid else ""}<br><b>Port:</b> {esc(c.get("udp_listen_port",7001))}<br><b>Erwartetes Präfix:</b> <code>{esc(c.get("command_prefix","velux.cmd"))}</code></p>')
    if rx_state:
        print(f'<p><b>Letztes UDP-Paket:</b> {esc(fmt_ts(rx_state.get("timestamp")))} von {esc(rx_state.get("source_ip",""))}:{esc(rx_state.get("source_port",""))}<br><code>{esc(rx_state.get("text",""))}</code><br><b>Erkannt:</b> {"Ja" if rx_state.get("parsed") else "Nein"}</p>')
    else:
        print('<p class="muted">Noch kein UDP-Paket empfangen.</p>')
    print('<form method="post"><input type="hidden" name="page" value="control"><button class="btn secondary" name="action" value="udp_selftest">UDP Listener Selbsttest</button></form></div>')
    if control_state:
        ok=bool(control_state.get("ok"))
        print(f'<div class="card {"okbox" if ok else "badbox"}"><h3>Letzter Steuerbefehl</h3><b>Quelle:</b> {esc(control_state.get("source","UDP"))}<br><b>Befehl:</b> <code>{esc(control_state.get("command","-"))}</code><br><b>Gerät:</b> {esc(control_state.get("device","-"))}<br><b>Ergebnis:</b> {esc(control_state.get("result","-"))}<br><b>Zeit:</b> {esc(fmt_ts(control_state.get("timestamp")))}</div>')
    devices=[d for d in state.get("devices",[]) if d.get("role")=="Aktor"]
    if devices:
        print('<div class="card"><h2>Direktsteuerung</h2><p class="muted">Mit diesen Buttons wird der Befehl sofort an die VELUX-Cloud gesendet.</p>')
        for d in devices:
            key=d.get("udp_key") or d.get("id")
            pos=pick(d,"current_position","position","target_position",default="-")
            print('<div style="padding:12px 0;border-bottom:1px solid #eee">')
            print(f'<div><b>{esc(d.get("name"))}</b> <span class="badge">{esc(d.get("type",""))}</span><br><span class="muted">{esc(d.get("room_name",""))} · Position: {esc(pos)} % · <code>{esc(key)}</code></span></div>')
            default_pos=pos if isinstance(pos,(int,float)) else 50
            print(f'<form method="post" class="ctrlrow" style="margin-top:8px"><input type="hidden" name="page" value="control"><input type="hidden" name="control_device" value="{esc(key)}"><button class="btn up" name="action" value="control_open">AUF</button><button class="btn stop" name="action" value="control_stop">STOP</button><button class="btn down" name="action" value="control_close">ZU</button><input type="number" name="control_value" min="0" max="100" step="1" value="{esc(default_pos)}"><button class="btn secondary" name="action" value="control_position">Position fahren</button></form>')
            prefix=c.get("command_prefix","velux.cmd")
            lbip=loxberry_ip()
            port=c.get("udp_listen_port",7001)
            print('<details style="margin-top:10px"><summary><b>Loxone Beispiel anzeigen</b></summary><div style="padding:10px 0">')
            print(f'<p><b>Virtueller UDP-Ausgang – Adresse</b><br><code>/dev/udp/{esc(lbip)}/{esc(port)}</code><br><b>Verbindung nach Senden schließen:</b> aktivieren</p>')
            print(f'<p><b>AUF – Befehl bei EIN</b><br><code>{esc(prefix)}.{esc(key)}.open=1</code><br><span class="muted">Befehl bei AUS: leer lassen</span></p>')
            print(f'<p><b>STOP – Befehl bei EIN</b><br><code>{esc(prefix)}.{esc(key)}.stop=1</code><br><span class="muted">Befehl bei AUS: leer lassen</span></p>')
            print(f'<p><b>ZU – Befehl bei EIN</b><br><code>{esc(prefix)}.{esc(key)}.close=1</code><br><span class="muted">Befehl bei AUS: leer lassen</span></p>')
            print(f'<p><b>POSITION – analoger Ausgangsbefehl</b><br><code>{esc(prefix)}.{esc(key)}.position=&lt;v&gt;</code><br><span class="muted">&lt;v&gt; wird von Loxone durch den Analogwert 0–100 ersetzt.</span></p>')
            print('</div></details>')
            print('</div>')
        print('</div>')
    else:
        print('<div class="card"><p class="muted">Aktuell wurde noch kein Gerät mit Positionswert als Aktor erkannt. Bitte zuerst auf der Statusseite VELUX-Daten abrufen.</p></div>')
elif page=="log":
    print('<div class="card"><div class="section-head"><div><h2>Log</h2><div class="muted">Zeigt API-Abrufe, gesendete UDP-Telegramme, empfangene Steuerbefehle und Fehler. Neueste Einträge stehen unten.</div></div></div><pre>'+esc("\n".join(log_lines) if log_lines else "Noch kein Log vorhanden.")+'</pre></div>')
else:
    status="Noch kein Abruf"; cls=""
    if state: status="Verbunden" if state.get("ok") else "Fehler"; cls="ok" if state.get("ok") else "bad"
    print(f'<div class="card"><h2>Status: <span class="{cls}">{status}</span></h2>')
    signing=cfg.get("signing",{}) if isinstance(cfg.get("signing",{}),dict) else {}
    paired=bool(signing.get("sign_key_id") and signing.get("hash_sign_key"))
    print(f'<h2>Gateway Kopplung: <span class="{"ok" if paired else "bad"}">{"Gekoppelt" if paired else "Nicht gekoppelt"}</span></h2>')
    plugin_enabled=bool(cfg.get("plugin_enabled",True))
    plugin_state="🟢 Aktiv" if plugin_enabled else "⚪ Inaktiv"
    plugin_btn="Plugin deaktivieren" if plugin_enabled else "Plugin aktivieren"
    plugin_btn_class="secondary" if plugin_enabled else "primary"
    print(f'<div style="margin:10px 0 18px"><b>Plugin:</b> {plugin_state} <form method="post" style="display:inline;margin-left:10px"><input type="hidden" name="page" value="status"><button class="btn {plugin_btn_class}" name="action" value="toggle_plugin">{plugin_btn}</button></form></div>')
    if state:
        interval=max(1,int(cfg.get("poll_interval_minutes",5)))
        last_started=float(run_state.get("started_at",run_state.get("timestamp",0)) or 0)
        next_run=scheduler_last_success+interval*60 if scheduler_last_success else None
        next_run_text=fmt_ts(next_run) if next_run else "noch nicht geplant"
        print(f'<div class="grid"><div><b>Letzter Abruf</b><br>{esc(fmt_ts(state.get("timestamp")))}</div><div><b>Abrufintervall</b><br>{interval} min</div><div><b>Nächster Lauf ab</b><br>{esc(next_run_text)}</div><div><b>Homes</b><br>{len(state.get("homes",[]))}</div><div><b>Räume</b><br>{len(state.get("rooms",[]))}</div><div><b>Geräte</b><br>{len(state.get("devices",[]))}</div><div><b>Werte</b><br>{len(state.get("values",{}))}</div><div><b>UDP gesendet</b><br>{esc(state.get("udp_messages",0))}</div></div>')
        if state.get("error"): print(f'<p class="bad"><b>Fehler:</b> {esc(state.get("error"))}</p>')
        if state.get("udp_error"): print(f'<p class="bad"><b>UDP-Warnung:</b> {esc(state.get("udp_error"))}</p>')
    print('<form method="post"><input type="hidden" name="page" value="status"><button class="btn primary" name="action" value="fetch">VELUX Daten jetzt abrufen</button><button class="btn ghost" name="action" value="relogin">Login komplett neu testen</button></form></div>')
    homes=state.get("homes",[])
    if homes:
        print('<div class="card"><h2>Homes</h2><table class="responsive"><thead><tr><th>Name</th><th>Räume</th><th>Geräte</th></tr></thead><tbody>')
        for h in homes:print(f'<tr><td data-label="Name"><b>{esc(h.get("name",""))}</b></td><td data-label="Räume">{esc(h.get("room_count",0))}</td><td data-label="Geräte">{esc(h.get("module_count",0))}</td></tr>')
        print('</tbody></table></div>')
    devices=state.get("devices",[])
    if devices:
        print('<div class="card"><h2>Geräte</h2><table class="responsive"><thead><tr><th>Name</th><th>Raum</th><th>Rolle / Typ</th><th>Position</th><th>UDP-Schlüssel</th></tr></thead><tbody>')
        for d in devices:
            pos=d.get("current_position",d.get("target_position",d.get("position","-")))
            print(f'<tr><td data-label="Name"><b>{esc(d.get("name",""))}</b></td><td data-label="Raum">{esc(d.get("room_name","-"))}</td><td data-label="Rolle / Typ">{esc(d.get("role",""))}<br><code>{esc(d.get("type",""))}</code></td><td data-label="Position">{esc(pos)}</td><td data-label="UDP-Schlüssel"><code>{esc(d.get("udp_key",""))}</code></td></tr>')
        print('</tbody></table></div>')
    vals=state.get("values",{}); meta=state.get("value_meta",{})
    if vals:
        print('<div class="card"><h2>Aktuelle Werte</h2><table class="responsive current-values-table"><thead><tr><th>Wert</th><th>Aktuell</th><th>VELUX Schlüssel</th></tr></thead><tbody>')
        for k in sorted(vals):
            m=meta.get(k,{})
            print(f'<tr><td data-label="Wert"><b>{esc(m.get("label",k))}</b></td><td data-label="Aktuell">{esc(display_value(vals[k],m))} {esc(m.get("unit",""))}</td><td data-label="VELUX Schlüssel"><code>{esc(k)}</code></td></tr>')
        print('</tbody></table></div>')
print('</div>')
