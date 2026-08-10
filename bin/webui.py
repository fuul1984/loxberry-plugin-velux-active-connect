from __future__ import annotations
import html, json, os, subprocess, sys, time, urllib.parse
from pathlib import Path
PLUGIN="veluxactive"; VERSION="0.5.12"
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
    cfg["udp_enabled"]="udp_enabled" in form
    cfg["miniserver_no"]=max(1,int(form.get("miniserver_no",cfg.get("miniserver_no",1))))
    cfg["udp_port"]=int(form.get("udp_port",cfg.get("udp_port",7000)))
    cfg["udp_prefix"]=form.get("udp_prefix",cfg.get("udp_prefix","velux")).strip() or "velux"
    cfg["heartbeat_enabled"]="heartbeat_enabled" in form
    cfg["udp_heartbeat_key"]=form.get("udp_heartbeat_key",cfg.get("udp_heartbeat_key","heartbeat")).strip() or "heartbeat"
    cfg["udp_auto_new"]="udp_auto_new" in form
    old_mode=str(cfg.get("udp_send_mode","always"))
    mode=form.get("udp_send_mode",old_mode)
    cfg["udp_send_mode"]=mode if mode in ("always","changed") else "always"
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
    cfg["control"]=c; save_cfg(cfg)

try:
    if action=="save_settings": save_main_settings(); message="Einstellungen gespeichert."; message_cls="okbox"; page="settings"
    elif action=="save_udp": save_udp_settings(); message="UDP-Messages gespeichert."; message_cls="okbox"; page="udp"
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
try: log_lines=log_file.read_text(encoding="utf-8",errors="replace").splitlines()[-80:]
except: log_lines=[]
def checked(v):return "checked" if v else ""
def nav(name,label):return f'<a class="nav {"active" if page==name else ""}" href="?page={name}">{label}</a>'

print(f'''<style>
*{{box-sizing:border-box}}.wrap{{max-width:1180px;margin:18px auto;padding:0 10px}}.hero{{background:#ef7d00;color:#fff;padding:18px 22px;border-radius:10px;display:flex;align-items:center;gap:16px}}.hero img{{width:54px;height:54px}}.hero h1{{margin:0}}.tabs{{display:flex;gap:7px;flex-wrap:wrap;margin:14px 0}}.nav{{padding:10px 15px;background:#e9edf0;color:#223!important;text-decoration:none!important;border-radius:7px;font-weight:bold}}.nav.active{{background:#34495e;color:#fff!important}}.card{{background:#fff;padding:18px;border-radius:10px;margin:12px 0;box-shadow:0 1px 7px #0001}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:13px}}label{{display:block;font-weight:bold;margin:0 0 5px}}input[type=text],input[type=password],input[type=number],select{{width:100%;padding:9px;border:1px solid #ccd2d8;border-radius:6px}}.btn{{border:0;border-radius:7px;padding:10px 16px;font-weight:bold;cursor:pointer;margin:3px}}.primary{{background:#ef7d00;color:white}}.secondary{{background:#34495e;color:white}}.ghost{{background:#e9edf0}}.ok{{color:#16833b}}.bad{{color:#c0392b}}.okbox{{background:#eaf7ee;border-left:5px solid #16833b}}.badbox{{background:#fdeeee;border-left:5px solid #c0392b}}table{{width:100%;border-collapse:collapse}}td,th{{padding:8px;border-bottom:1px solid #eee;text-align:left;vertical-align:middle}}code{{font-size:12px}}pre{{white-space:pre-wrap;word-break:break-word;background:#111;color:#eee;padding:12px;border-radius:7px;max-height:360px;overflow:auto}}.muted{{color:#667;font-size:13px}}.badge{{display:inline-block;padding:3px 8px;border-radius:15px;background:#eef1f3;font-size:12px}}.switchline{{display:flex;gap:8px;align-items:center}}.udpname{{min-width:300px}}.ctrlrow{{display:flex;gap:7px;align-items:center;flex-wrap:wrap}}.ctrlrow input[type=number]{{width:90px}}.up{{background:#16833b;color:white}}.stop{{background:#d89b00;color:white}}.down{{background:#c0392b;color:white}}</style>
<div class="wrap"><div class="hero"><img src="icon_128.png" alt="VELUX Active Connect"><div><h1>VELUX Active Connect <small>{VERSION}</small></h1><div>VELUX ACTIVE / App Control → LoxBerry → Loxone</div></div></div>
<div class="tabs">{nav('status','Status')}{nav('settings','Einstellungen')}{nav('udp','UDP Messages')}{nav('control','Steuerung')}{nav('log','Log')}</div>''')
if message: print(f'<div class="card {message_cls}"><b>{esc(message)}</b></div>')

if page=="settings":
    print('<form method="post"><input type="hidden" name="page" value="settings">')
    print('<div class="card"><h2>VELUX Einstellungen</h2><div class="grid">')
    print(f'<div><label>E-Mail</label><input type="text" name="email" value="{esc(cfg.get("email",""))}"></div>')
    print('<div><label>Passwort</label><input type="password" name="password" placeholder="unverändert lassen"></div>')
    print(f'<div><label>Abrufintervall (Minuten)</label><input type="number" min="1" name="poll_interval_minutes" value="{esc(cfg.get("poll_interval_minutes",5))}"></div></div></div>')
    print('<div class="card"><h2>UDP Statuswerte an Loxone senden</h2><div class="grid">')
    print(f'<div><label class="switchline"><input type="checkbox" name="udp_enabled" {checked(cfg.get("udp_enabled"))}> UDP senden aktiv</label></div>')
    print('<div><label>Miniserver aus LoxBerry</label><select name="miniserver_no">')
    selected=int(cfg.get("miniserver_no",1) or 1)
    if miniservers:
        for i,ms in enumerate(miniservers,1):
            no=int(pick(ms,"_msno",default=i) or i); name=pick(ms,"Name","name",default=f"Miniserver {no}"); ip=pick(ms,"IPAddress","ipaddress","IP","ip",default=""); sel=" selected" if no==selected else ""
            print(f'<option value="{no}"{sel}>{esc(name)}{esc(" — "+ip if ip else "")}</option>')
    else: print('<option value="1">Kein Miniserver gefunden</option>')
    print('</select></div>')
    print(f'<div><label>UDP Sendeport zum Miniserver</label><input type="number" name="udp_port" min="1" max="65535" value="{esc(cfg.get("udp_port",7000))}"></div>')
    print(f'<div><label>UDP Status-Präfix</label><input type="text" name="udp_prefix" value="{esc(cfg.get("udp_prefix","velux"))}"></div>')
    print(f'<div><label class="switchline"><input type="checkbox" name="heartbeat_enabled" {checked(cfg.get("heartbeat_enabled",True))}> Heartbeat senden</label></div>')
    print(f'<div><label>Heartbeat-Name</label><input type="text" name="udp_heartbeat_key" value="{esc(cfg.get("udp_heartbeat_key","heartbeat"))}"></div>')
    print(f'<div><label class="switchline"><input type="checkbox" name="udp_auto_new" {checked(cfg.get("udp_auto_new",True))}> Neue Werte automatisch für UDP aktivieren</label></div>')
    print(f'<div><label>UDP-Sendeverhalten</label><select name="udp_send_mode"><option value="always" {"selected" if cfg.get("udp_send_mode","always")=="always" else ""}>Alle Werte bei jedem Abruf senden</option><option value="changed" {"selected" if cfg.get("udp_send_mode")=="changed" else ""}>Nur geänderte Werte senden</option></select></div></div>')
    print('<p class="muted">Sendeport = Statuswerte vom LoxBerry zum Miniserver.</p></div>')
    c=cfg.get("control",{}) if isinstance(cfg.get("control",{}),dict) else {}
    print('<div class="card"><h2>Loxone → VELUX Steuerung</h2><div class="grid">')
    print(f'<div><label class="switchline"><input type="checkbox" name="control_enabled" {checked(c.get("enabled",False))}> UDP-Steuerung von Loxone aktivieren</label></div>')
    print(f'<div><label>UDP Empfangsport am LoxBerry</label><input type="number" min="1" max="65535" name="control_udp_listen_port" value="{esc(c.get("udp_listen_port",7001))}"></div>')
    print(f'<div><label>Befehls-Präfix</label><input type="text" name="control_command_prefix" value="{esc(c.get("command_prefix","velux.cmd"))}"></div></div>')
    print('<p class="muted">Empfangsport = Steuerbefehle vom Miniserver zum LoxBerry. Dieser Port wird auch in der Loxone-Hilfe angezeigt.</p></div>')
    signing=cfg.get("signing",{}) if isinstance(cfg.get("signing",{}),dict) else {}
    gateways=[d for d in state.get("devices",[]) if str(d.get("type","")).upper()=="NXG"]
    print('<div class="card"><h2>VELUX Gateway Kopplung</h2>')
    try:
        dep=subprocess.run([sys.executable,"-c","import cryptography; print(cryptography.__version__)"],capture_output=True,text=True,timeout=5)
        if dep.returncode==0:
            print(f'<div class="okbox"><b>Kryptografie bereit:</b> cryptography {esc(dep.stdout.strip())}</div>')
        else:
            print('<div class="badbox"><b>Kryptografie fehlt.</b> Details im Log dependencies.log.</div>')
    except Exception as e:
        print(f'<div class="badbox"><b>Kryptografie-Prüfung fehlgeschlagen:</b> {esc(e)}</div>')
    if signing.get("sign_key_id") and signing.get("hash_sign_key"):
        print(f'<div class="okbox"><b>Gateway gekoppelt</b><br>Gateway-ID: <code>{esc(signing.get("gateway_id",""))}</code><br>Gateway-IP: {esc(signing.get("gateway_ip",""))}<br>Gekoppelt am: {esc(fmt_ts(signing.get("paired_at")))}</div>')
    else:
        print('<div class="badbox"><b>Gateway nicht gekoppelt</b><br>Für signierte Dachfenster-Positionen ist eine Kopplung nötig.</div>')
    print('<div class="grid">')
    print(f'<div><label>Gateway-IP</label><input type="text" name="gateway_ip" value="{esc(signing.get("gateway_ip",""))}" placeholder="192.168.1.x"></div>')
    print('<div><label>Gateway</label><select name="gateway_id">')
    if gateways:
        for g in gateways:
            sel=' selected' if g.get("id")==signing.get("gateway_id") else ''
            print(f'<option value="{esc(g.get("id"))}"{sel}>{esc(g.get("name"))} – {esc(g.get("id"))}</option>')
    else:
        print('<option value="">Kein NXG-Gateway erkannt</option>')
    print('</select></div></div>')
    print('<p class="muted">Für die Kopplung muss der LoxBerry das Gateway auf TCP-Port 25050 erreichen können.</p>')
    print('<p><button class="btn secondary" name="action" value="pair_gateway">Gateway koppeln</button></p></div>')
    print('<p><button class="btn primary" name="action" value="save_settings">Einstellungen speichern</button></p></form>')
elif page=="udp":
    print('<form method="post"><input type="hidden" name="page" value="udp"><div class="card"><h2>UDP Messages</h2><p class="muted">Grundeinstellungen wie Miniserver, Sendeport, Präfix und Sendeverhalten findest du unter Einstellungen.</p>')
    vals=state.get("values",{}); meta=state.get("value_meta",{}); rules=cfg.get("udp_messages",{}) if isinstance(cfg.get("udp_messages",{}),dict) else {}
    print('<h2>Messages</h2><p class="muted">Jeder erkannte Wert kann einzeln aktiviert und umbenannt werden. Das globale Präfix wird beim Versand davor gesetzt.</p>')
    if vals:
        print('<table><tr><th>Senden</th><th>VELUX Wert</th><th>Aktuell</th><th>UDP Message</th></tr>')
        for i,key in enumerate(sorted(vals)):
            rule=rules.get(key,{}); en=rule.get("enabled",cfg.get("udp_auto_new",True)) if isinstance(rule,dict) else cfg.get("udp_auto_new",True); name=(rule.get("name") if isinstance(rule,dict) else None) or key; m=meta.get(key,{})
            print(f'<tr><td><input type="checkbox" name="udp_en_{i}" {checked(en)}><input type="hidden" name="udp_key_{i}" value="{esc(key)}"></td><td><b>{esc(m.get("label",key))}</b><br><code>{esc(key)}</code></td><td>{esc(display_value(vals[key],m))} {esc(m.get("unit",""))}</td><td><input class="udpname" type="text" name="udp_name_{i}" value="{esc(name)}"><br><span class="muted">{esc(cfg.get("udp_prefix","velux"))}.{esc(name)}</span></td></tr>')
        print(f'</table><input type="hidden" name="udp_count" value="{len(vals)}">')
    else: print('<p>Noch keine Werte vorhanden. Zuerst auf der Status-Seite VELUX-Daten abrufen.</p>')
    print('<p><button class="btn primary" name="action" value="save_udp">UDP Messages speichern</button></p></div></form>')
elif page=="control":
    c=cfg.get("control",{}) if isinstance(cfg.get("control",{}),dict) else {}
    print('<div class="card"><h2>Steuerung <span class="badge">v0.5.12</span></h2><p>Hier kannst du die erkannten VELUX-Aktoren direkt bedienen. Die Loxone-Konfiguration findest du unter <b>Einstellungen</b>.</p></div>')
    paired=bool((cfg.get("signing") or {}).get("sign_key_id") and (cfg.get("signing") or {}).get("hash_sign_key"))
    print('<div class="card"><h2>VELUX ACTIVE Automatisierung</h2>')
    print('<p>Gibt die VELUX ACTIVE Klima-Automatik mit dem signierten Gateway-Scenario <code>home</code> wieder frei.</p>')
    if paired:
        print('<form method="post"><input type="hidden" name="page" value="control"><button class="btn primary" name="action" value="control_automation">Automatisierung aktivieren</button></form>')
        print('<p><b>Loxone UDP:</b> <code>velux.cmd.velux_active.automation=1</code></p>')
    else:
        print('<p><b>Gateway nicht gekoppelt.</b> Dieser Befehl benötigt die Gateway-Kopplung.</p>')
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
    print('<div class="card"><h2>Log</h2><pre>'+esc("\n".join(log_lines) if log_lines else "Noch kein Log vorhanden.")+'</pre></div>')
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
        print('<div class="card"><h2>Homes</h2><table><tr><th>Name</th><th>Räume</th><th>Geräte</th></tr>')
        for h in homes:print(f'<tr><td><b>{esc(h.get("name",""))}</b></td><td>{esc(h.get("room_count",0))}</td><td>{esc(h.get("module_count",0))}</td></tr>')
        print('</table></div>')
    devices=state.get("devices",[])
    if devices:
        print('<div class="card"><h2>Geräte</h2><table><tr><th>Name</th><th>Raum</th><th>Rolle / Typ</th><th>Position</th><th>UDP-Schlüssel</th></tr>')
        for d in devices:
            pos=d.get("current_position",d.get("target_position",d.get("position","-")))
            print(f'<tr><td><b>{esc(d.get("name",""))}</b></td><td>{esc(d.get("room_name","-"))}</td><td>{esc(d.get("role",""))}<br><code>{esc(d.get("type",""))}</code></td><td>{esc(pos)}</td><td><code>{esc(d.get("udp_key",""))}</code></td></tr>')
        print('</table></div>')
    vals=state.get("values",{}); meta=state.get("value_meta",{})
    if vals:
        print('<div class="card"><h2>Aktuelle Werte</h2><table><tr><th>Wert</th><th>Aktuell</th><th>VELUX Schlüssel</th></tr>')
        for k in sorted(vals):
            m=meta.get(k,{})
            print(f'<tr><td><b>{esc(m.get("label",k))}</b></td><td>{esc(display_value(vals[k],m))} {esc(m.get("unit",""))}</td><td><code>{esc(k)}</code></td></tr>')
        print('</table></div>')
print('</div>')
