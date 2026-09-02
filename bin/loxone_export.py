#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, re, sys, socket
from pathlib import Path

PLUGIN="veluxactive"
CFG=Path(os.environ.get("LBPCONFIGDIR") or f"/opt/loxberry/config/plugins/{PLUGIN}")
DATA=Path(os.environ.get("LBPDATADIR") or f"/opt/loxberry/data/plugins/{PLUGIN}")
OUT=DATA/"exports"
CONFIG=CFG/"config.json"
STATE=DATA/"state.json"

def load(p,d):
    try:return json.loads(p.read_text(encoding="utf-8"))
    except Exception:return d

def safe(s):
    s=str(s or "").strip().lower()
    repl={"ä":"ae","ö":"oe","ü":"ue","ß":"ss","é":"e","è":"e","à":"a","á":"a","ç":"c"}
    for a,b in repl.items(): s=s.replace(a,b)
    s=re.sub(r"[^a-z0-9]+","_",s).strip("_")
    return s or "wert"

def detect_local_ip():
    # Determine the address used to reach the LAN/default route.
    try:
        sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8",80))
        ip=sock.getsockname()[0]
        sock.close()
        if ip and not ip.startswith("127."): return ip
    except Exception:
        pass
    try:
        ips=socket.gethostbyname_ex(socket.gethostname())[2]
        for ip in ips:
            if ip and not ip.startswith("127."): return ip
    except Exception:
        pass
    return "LOXBERRY_IP"

def write(name,text):
    OUT.mkdir(parents=True,exist_ok=True)
    p=OUT/name
    p.write_text(text,encoding="utf-8")
    return str(p)

def build():
    cfg=load(CONFIG,{})
    state=load(STATE,{})
    ctl=cfg.get("control",{}) if isinstance(cfg.get("control"),dict) else {}

    # UDP settings are stored flat in config.json. Respect the exact configured
    # prefix and per-value UDP names used by worker.py.
    prefix=str(cfg.get("udp_prefix","velux") or "velux").strip(".")
    listen_port=int(ctl.get("udp_listen_port",7001))
    cmd_prefix=str(ctl.get("command_prefix","velux.cmd") or "velux.cmd").strip(".")
    loxberry_ip=detect_local_ip()
    udp_address=f"/dev/udp/{loxberry_ip}/{listen_port}"
    # Build the same enabled/name mapping as worker.py so exports match the
    # messages actually sent to Loxone.
    messages=[]
    rules=cfg.get("udp_messages",{}) if isinstance(cfg.get("udp_messages"),dict) else {}
    auto_new=bool(cfg.get("udp_auto_new",True))
    meta=state.get("value_meta",{}) if isinstance(state.get("value_meta"),dict) else {}
    for key,val in sorted((state.get("values") or {}).items()):
        rule=rules.get(key)
        enabled=auto_new if not isinstance(rule,dict) else bool(rule.get("enabled",True))
        if not enabled:
            continue
        udp_name=key if not isinstance(rule,dict) else (rule.get("name") or key)
        item=dict(meta.get(key,{}) if isinstance(meta.get(key,{}),dict) else {})
        item.setdefault("label",key)
        messages.append((udp_name,key,item))

    devices=[d for d in state.get("devices",[]) if d.get("role")=="Aktor"]

    # Human-readable text import helper
    status_lines=[
        "# VELUX Active Connect - Loxone UDP Eingänge",
        f"# Status-Präfix: {prefix}",
        "# Format pro virtueller UDP-Eingang:",
        "# Name | Suchmuster",
        ""
    ]
    for udp_name,key,item in messages:
        full=f"{prefix}.{udp_name}"
        label=item.get("label") or key
        status_lines.append(f"{label} | {full}=\\v")

    cmd_lines=[
        "# VELUX Active Connect - Loxone UDP Befehle",
        f"# Virtueller UDP-Ausgang Adresse: {udp_address}",
        "# In Loxone Config 'Verbindung nach Senden schließen' aktivieren.",
        f"# Befehls-Präfix: {cmd_prefix}",
        "# Digitale Befehle in 'Befehl bei EIN'; Befehl bei AUS leer lassen.",
        "# POSITION ist analog und verwendet <v> als Ausgangswert.",
        ""
    ]
    for d in devices:
        key=d.get("udp_key") or d.get("id")
        name=d.get("name") or key
        cmd_lines += [
            f"[{name}]",
            f"AUF={cmd_prefix}.{key}.open=1",
            f"STOP={cmd_prefix}.{key}.stop=1",
            f"ZU={cmd_prefix}.{key}.close=1",
            f"POSITION={cmd_prefix}.{key}.position=<v>",
            ""
        ]

    # CSVs are easiest to copy/import/reference from Loxone Config
    import csv, io
    sio=io.StringIO()
    w=csv.writer(sio,delimiter=";")
    w.writerow(["Name","UDP Suchmuster","Beschreibung"])
    for udp_name,key,item in messages:
        label=item.get("label") or key
        w.writerow([label,f"{prefix}.{udp_name}=\\v",key])
    status_csv=sio.getvalue()

    sio=io.StringIO()
    w=csv.writer(sio,delimiter=";")
    w.writerow(["Gerät","Befehl","UDP Nachricht","Virtueller UDP-Ausgang Adresse","Hinweis"])
    for d in devices:
        key=d.get("udp_key") or d.get("id")
        name=d.get("name") or key
        for label,msg in [
            ("AUF",f"{cmd_prefix}.{key}.open=1"),
            ("STOP",f"{cmd_prefix}.{key}.stop=1"),
            ("ZU",f"{cmd_prefix}.{key}.close=1"),
            ("POSITION",f"{cmd_prefix}.{key}.position=<v>"),
        ]:
            hint="Befehl bei EIN; AUS leer" if label!="POSITION" else "Analogwert; <v> wird durch Wert ersetzt"
            w.writerow([name,label,msg,udp_address,hint])
    commands_csv=sio.getvalue()

    # XML-like snippet for copy/paste/reference, not pretending to be a native Loxone project file
    xml=["<?xml version=\"1.0\" encoding=\"UTF-8\"?>",
         "<VeluxActiveLoxoneExport version=\"1\">",
         f'  <Status prefix="{prefix}">']
    for udp_name,key,item in messages:
        label=str(item.get("label") or key).replace("&","&amp;").replace('"',"&quot;")
        patt=f"{prefix}.{udp_name}=\\v".replace("&","&amp;").replace('"',"&quot;")
        xml.append(f'    <Input name="{label}" pattern="{patt}" />')
    xml.append("  </Status>")
    xml.append(f'  <Commands udpPort="{listen_port}" prefix="{cmd_prefix}" address="{udp_address}">')
    for d in devices:
        key=d.get("udp_key") or d.get("id")
        name=str(d.get("name") or key).replace("&","&amp;").replace('"',"&quot;")
        xml.append(f'    <Device name="{name}" key="{key}">')
        xml.append(f'      <Command name="AUF">{cmd_prefix}.{key}.open=1</Command>')
        xml.append(f'      <Command name="STOP">{cmd_prefix}.{key}.stop=1</Command>')
        xml.append(f'      <Command name="ZU">{cmd_prefix}.{key}.close=1</Command>')
        xml.append(f'      <Command name="POSITION">{cmd_prefix}.{key}.position=\\v</Command>')
        xml.append("    </Device>")
    xml.append("  </Commands>")
    xml.append("</VeluxActiveLoxoneExport>")

    files={
        "status_txt":write("loxone_udp_inputs.txt","\n".join(status_lines)+"\n"),
        "commands_txt":write("loxone_udp_commands.txt","\n".join(cmd_lines)+"\n"),
        "status_csv":write("loxone_udp_inputs.csv",status_csv),
        "commands_csv":write("loxone_udp_commands.csv",commands_csv),
        "xml":write("loxone_velux_export.xml","\n".join(xml)+"\n")
    }
    meta={"files":files,"status_count":len(messages),"device_count":len(devices),
          "udp_port":listen_port,"loxberry_ip":loxberry_ip,"udp_address":udp_address,
          "status_prefix":prefix,"command_prefix":cmd_prefix}
    write("export_meta.json",json.dumps(meta,indent=2,ensure_ascii=False))
    return meta

if __name__=="__main__":
    print(json.dumps(build(),ensure_ascii=False))
