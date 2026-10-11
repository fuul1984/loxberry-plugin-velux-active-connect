#!/usr/bin/env python3
import json,os,re,signal,subprocess,sys,time
from pathlib import Path
CFG=Path(os.environ.get('LBPCONFIGDIR','/opt/loxberry/config/plugins/veluxactive')); DATA=Path(os.environ.get('LBPDATADIR','/opt/loxberry/data/plugins/veluxactive')); LOG=Path(os.environ.get('LBPLOGDIR','/opt/loxberry/log/plugins/veluxactive'))
PAIR=CFG/'homekit_pairing.json'; CHARS=DATA/'event_characteristics.json'; STATUS=DATA/'event_status.json'; PID=DATA/'event_listener.pid'; CONFIG=CFG/'config.json'; STATE=DATA/'state.json'; UDP_LAST=DATA/'udp_last_sent.json'; ALIAS='velux_events'; MAPPING=DATA/'hap_device_mapping.json'; LEARN=DATA/'hap_mapping_pending.json'; LOCAL=DATA/'local_values.json'; LOCALMAP=DATA/'hap_local_mapping.json'
STOP=False; CHILD=None
EVENT_VALUES={}

def log(s):
    LOG.mkdir(parents=True,exist_ok=True)
    with open(LOG/'veluxactive.log','a',encoding='utf-8') as f: f.write(time.strftime('%Y-%m-%d %H:%M:%S')+' EVENT '+s+'\n')
def save(**kw):
    try: d=json.loads(STATUS.read_text(encoding='utf-8'))
    except: d={}
    d.update(kw); STATUS.parent.mkdir(parents=True,exist_ok=True); STATUS.write_text(json.dumps(d,indent=2,ensure_ascii=False),encoding='utf-8')
def stop(sig=None,frame=None):
    global STOP,CHILD
    STOP=True; log('LISTENER STOP angefordert')
    if CHILD and CHILD.poll() is None:
        try: CHILD.terminate()
        except: pass
signal.signal(signal.SIGTERM,stop); signal.signal(signal.SIGINT,stop)

def load_ids():
    try:
        chars=json.loads(CHARS.read_text(encoding='utf-8'))
        ids=[x['id'] for x in chars if isinstance(x,dict) and x.get('id')]
        if ids:
            return ids
    except Exception:
        pass

    # Productive self-initialisation: a valid HAP pairing is sufficient.
    # The former diagnostic button must not be required after install/reboot.
    if not PAIR.exists():
        raise RuntimeError('Eventstream ist nicht gekoppelt.')
    log('AUTO INIT -> Event-Characteristics fehlen; werden aus vorhandener HAP-Kopplung gelesen')
    setup=Path(__file__).resolve().parent/'event_setup.py'
    r=subprocess.run([sys.executable,str(setup),'accessories'],capture_output=True,text=True,timeout=60,
                     env={**os.environ,'LBPCONFIGDIR':str(CFG),'LBPDATADIR':str(DATA),'LBPLOGDIR':str(LOG)})
    if r.returncode != 0:
        raise RuntimeError('Automatische Eventstream-Initialisierung fehlgeschlagen: '+(r.stderr.strip() or r.stdout.strip() or 'unbekannter Fehler'))
    try:
        chars=json.loads(CHARS.read_text(encoding='utf-8'))
        ids=[x['id'] for x in chars if isinstance(x,dict) and x.get('id')]
    except Exception as e:
        raise RuntimeError('Automatische Eventstream-Initialisierung lieferte keine gültigen Characteristics: '+str(e))
    if not ids:
        raise RuntimeError('Automatische Eventstream-Initialisierung fand keine eventfähigen Characteristics.')
    log('AUTO INIT OK -> '+str(len(ids))+' Event-Characteristics eingerichtet')
    return ids


def load_json(path, default):
    try: return json.loads(path.read_text(encoding='utf-8'))
    except Exception: return default

def slug(s):
    text=str(s).strip().translate(str.maketrans({'ä':'ae','ö':'oe','ü':'ue','Ä':'Ae','Ö':'Oe','Ü':'Ue','ß':'ss'}))
    return re.sub(r'[^a-zA-Z0-9_]+','_',text).strip('_').lower() or 'unknown'

def udp_path(value):
    return '.'.join(slug(x) for x in str(value).split('.') if str(x).strip()) or 'value'

def position_key():
    state=load_json(STATE,{})
    values=state.get('values',{}) if isinstance(state,dict) else {}
    keys=[k for k in values if str(k).startswith('module.') and str(k).endswith('.position')]
    if len(keys)==1: return keys[0]
    if not keys: return None
    # Multiple windows need explicit HAP accessory-to-module mapping; never guess.
    log('UDP SKIP -> mehrere Positionswerte vorhanden, HAP-Zuordnung ist nicht eindeutig: '+', '.join(keys))
    return None

def send_position_udp(value, source):
    cfg=load_json(CONFIG,{})
    if not cfg.get('udp_enabled'): return False
    key=position_key()
    if not key:
        log('UDP SKIP -> kein eindeutiger bestehender Fenster-Positionswert gefunden')
        return False
    rules=cfg.get('udp_messages',{}) if isinstance(cfg.get('udp_messages',{}),dict) else {}
    rule=rules.get(key)
    enabled=bool(cfg.get('udp_auto_new',True)) if not isinstance(rule,dict) else bool(rule.get('enabled',True))
    if not enabled:
        log('UDP SKIP -> '+key+' ist in UDP-Messages deaktiviert')
        return False
    target=key if not isinstance(rule,dict) else (rule.get('name') or key)
    target=udp_path(target)
    try:
        if isinstance(value,str) and value.lower() in ('null','none',''): return False
        number=float(value)
        value=int(number) if number.is_integer() else number
    except (TypeError,ValueError):
        log('UDP SKIP -> ungültiger Positionswert '+repr(value))
        return False
    mode=str(cfg.get('udp_send_mode','always') or 'always').lower()
    cache=load_json(UDP_LAST,{}) if mode=='changed' else {}
    try: boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    except Exception: boot_id='unknown'
    last_sent=cache.get('values',{}) if isinstance(cache,dict) and cache.get('boot_id')==boot_id and isinstance(cache.get('values'),dict) else {}
    if mode=='changed' and last_sent.get(target)==value:
        log(f'UDP SKIP -> {target}={value} unverändert ({source})')
        return False
    msno=max(1,int(cfg.get('miniserver_no',1))); port=int(cfg.get('udp_port',7000)); prefix=slug(cfg.get('udp_prefix','velux'))
    helper=Path(__file__).resolve().parent/'loxberry_bridge.pl'
    payload={target:value}
    r=subprocess.run([str(helper),'send',str(msno),str(port),prefix],input=json.dumps(payload,ensure_ascii=False),capture_output=True,text=True,timeout=30)
    if r.returncode!=0: raise RuntimeError('LoxBerry UDP: '+(r.stderr.strip() or r.stdout.strip() or 'unbekannter Fehler'))
    if mode=='changed':
        last_sent[target]=value
        tmp=UDP_LAST.with_suffix('.json.tmp')
        tmp.write_text(json.dumps({'boot_id':boot_id,'values':last_sent},indent=2,ensure_ascii=False),encoding='utf-8'); os.chmod(tmp,0o600); tmp.replace(UDP_LAST)
    log(f'UDP TX -> MS#{msno}:{port} {prefix}.{target}={value} [Eventstream {source}]')
    return True


def normalize_local_value(name, raw):
    n=str(name).strip().lower()
    if str(raw).strip().lower() in ('true','false'):
        return 1 if str(raw).strip().lower()=='true' else 0
    try:
        x=float(raw)
        if n=='relative-humidity.current' and 0 <= x <= 1:
            x*=100.0
        return int(x) if x.is_integer() else round(x,3)
    except (TypeError,ValueError):
        return raw

def local_candidates(name):
    state=load_json(STATE,{})
    values=state.get('values',{}) if isinstance(state,dict) else {}
    n=str(name).strip().lower()
    # Strict semantic aliases only. We deliberately do not map unknown HAP names by
    # ordering/AID. This makes the mechanism reusable for windows, shutters and
    # sensors without risking a value being assigned to the wrong VELUX device.
    aliases={
        'temperature.current': ('temperature',),
        'relative-humidity.current': ('humidity',),
        'carbon-dioxide.level': ('co2',),
        'light-level.current': ('lux','light'),
        'current-ambient-light-level': ('lux','light'),
        'battery-level': ('battery','battery_level'),
        'status-low-battery': ('low_battery','battery_low'),
    }
    tails=aliases.get(n,())
    tests={n: (lambda k,tails=tails: any(str(k).lower().endswith('.'+tail) for tail in tails))} if tails else {}
    fn=tests.get(n)
    return [k for k in values if fn and fn(k)]

def resolved_local_key(cid, name, aid):
    mapping=load_json(LOCALMAP,{})
    if isinstance(mapping,dict):
        e=mapping.get(str(cid))
        if isinstance(e,dict) and e.get('key'):
            return e.get('key')
    candidates=local_candidates(name)
    if len(candidates)!=1:
        return None
    key=candidates[0]
    if not isinstance(mapping,dict): mapping={}
    mapping[str(cid)]={'key':key,'name':name,'aid':aid,'method':'unique_cloud_value','mapped_at':int(time.time())}
    LOCALMAP.parent.mkdir(parents=True,exist_ok=True)
    tmp=LOCALMAP.with_suffix('.json.tmp'); tmp.write_text(json.dumps(mapping,indent=2,ensure_ascii=False),encoding='utf-8'); os.chmod(tmp,0o664); tmp.replace(LOCALMAP)
    log(f'LOCAL MAP -> {cid} {name} = {key} (eindeutig automatisch)')
    return key

def prepare_local_mappings():
    # Resolve every safely identifiable event value at listener start. Previously a
    # mapping appeared only after the first event, which made quiet values such as
    # humidity look like Cloud values after an update/reboot.
    count=0
    for cid,meta in characteristic_index().items():
        name=str(meta.get('name','')).strip().lower()
        if not name or name.startswith('position.'):
            continue
        try: aid=int(meta.get('aid',str(cid).split('.')[0]))
        except Exception: continue
        if resolved_local_key(cid,name,aid): count+=1
    log(f'LOCAL MAP INIT -> {count} lokale Wertzuordnung(en) eindeutig vorbereitet')
    return count

def save_local_value(key, value, cid, name, aid):
    data=load_json(LOCAL,{})
    if not isinstance(data,dict): data={}
    vals=data.get('values',{}) if isinstance(data.get('values'),dict) else {}
    vals[key]={'value':value,'timestamp':int(time.time()),'characteristic':cid,'name':name,'aid':aid,'source':'EVENTSTREAM'}
    data={'updated_at':int(time.time()),'values':vals}
    LOCAL.parent.mkdir(parents=True,exist_ok=True)
    tmp=LOCAL.with_suffix('.json.tmp'); tmp.write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding='utf-8'); os.chmod(tmp,0o664); tmp.replace(LOCAL)

def send_generic_udp(key, value, cid, name):
    cfg=load_json(CONFIG,{})
    if not cfg.get('udp_enabled'): return False
    rules=cfg.get('udp_messages',{}) if isinstance(cfg.get('udp_messages',{}),dict) else {}
    rule=rules.get(key)
    enabled=bool(cfg.get('udp_auto_new',True)) if not isinstance(rule,dict) else bool(rule.get('enabled',True))
    if not enabled: return False
    target=udp_path(key if not isinstance(rule,dict) else (rule.get('name') or key))
    mode=str(cfg.get('udp_send_mode','always') or 'always').lower()
    cache=load_json(UDP_LAST,{}) if mode=='changed' else {}
    try: boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    except Exception: boot_id='unknown'
    last_sent=cache.get('values',{}) if isinstance(cache,dict) and cache.get('boot_id')==boot_id and isinstance(cache.get('values'),dict) else {}
    if mode=='changed' and last_sent.get(target)==value:
        log(f'UDP SKIP -> {target}={value} unverändert [Eventstream {cid} {name}]'); return False
    msno=max(1,int(cfg.get('miniserver_no',1))); port=int(cfg.get('udp_port',7000)); prefix=slug(cfg.get('udp_prefix','velux'))
    helper=Path(__file__).resolve().parent/'loxberry_bridge.pl'
    r=subprocess.run([str(helper),'send',str(msno),str(port),prefix],input=json.dumps({target:value},ensure_ascii=False),capture_output=True,text=True,timeout=30)
    if r.returncode!=0: raise RuntimeError('LoxBerry UDP: '+(r.stderr.strip() or r.stdout.strip() or 'unbekannter Fehler'))
    if mode=='changed':
        last_sent[target]=value
        tmp=UDP_LAST.with_suffix('.json.tmp'); tmp.write_text(json.dumps({'boot_id':boot_id,'values':last_sent},indent=2,ensure_ascii=False),encoding='utf-8'); os.chmod(tmp,0o600); tmp.replace(UDP_LAST)
    log(f'UDP TX -> MS#{msno}:{port} {prefix}.{target}={value} [Eventstream {cid} {name}]')
    return True

def characteristic_index():
    chars=load_json(CHARS,[])
    return {str(c.get('id')):c for c in chars if isinstance(c,dict) and c.get('id')} if isinstance(chars,list) else {}

def learn_mapping(aid, raw):
    """Correlate a pending cloud command with the matching HAP target event.

    Mappings are learned only while a short-lived pending cloud-fallback command exists.
    A matching target event may correct an older conflicting mapping; no AID-order guess is used.
    """
    pending=load_json(LEARN,{})
    if not isinstance(pending,dict) or not pending:
        return False
    now=time.time()
    if now>float(pending.get('expires_at',0) or 0):
        try: LEARN.unlink()
        except Exception: pass
        return False
    try:
        target=int(float(raw)); expected=int(float(pending.get('target')))
    except Exception: return False
    if target!=expected: return False
    device_key=str(pending.get('device_key','')).strip(); position_key=str(pending.get('position_key','')).strip()
    if not device_key or not position_key: return False
    mapping=load_json(MAPPING,{})
    if not isinstance(mapping,dict): mapping={}
    # One HAP AID must map to exactly one cloud actuator and vice versa.
    # A fresh cloud-fallback -> matching HAP target correlation is stronger evidence
    # than an older learned mapping. This lets the plugin repair a wrong mapping
    # without guessing from AID order. The displaced device becomes deliberately
    # unmapped and will be learned again on its next cloud-fallback command.
    existing=mapping.get(str(aid))
    displaced=None
    if isinstance(existing,dict) and existing.get('device_key') not in (None,'',device_key):
        displaced=str(existing.get('device_key'))
        log(f'HAP MAP CORRECT -> AID {aid}: {displaced} wird durch {device_key} ersetzt (bestätigtes Cloud/Event-Target={target})')

    removed=[]
    for other_aid,entry in list(mapping.items()):
        if str(other_aid)!=str(aid) and isinstance(entry,dict) and entry.get('device_key')==device_key:
            removed.append(str(other_aid))
            del mapping[other_aid]
    if removed:
        log(f'HAP MAP CORRECT -> {device_key}: alte AID-Zuordnung(en) {", ".join(removed)} entfernt')

    mapping[str(aid)]={'device_key':device_key,'position_key':position_key,'learned_at':int(now),'method':'command_event_correlation_corrected' if displaced or removed else 'command_event_correlation'}
    MAPPING.parent.mkdir(parents=True,exist_ok=True)
    tmp=MAPPING.with_suffix('.json.tmp')
    tmp.write_text(json.dumps(mapping,indent=2,ensure_ascii=False),encoding='utf-8')
    os.chmod(tmp,0o664); tmp.replace(MAPPING)
    try: LEARN.unlink()
    except Exception: pass
    log(f'HAP MAP LEARNED -> {device_key} = AID {aid} (target={target})')
    return True

def mapped_position_key(aid):
    # KIX compatibility: one cloud actuator remains unambiguous regardless of HAP AID.
    state=load_json(STATE,{})
    values=state.get('values',{}) if isinstance(state,dict) else {}
    keys=[k for k in values if str(k).startswith('module.') and str(k).endswith('.position')]
    if len(keys)==1: return keys[0]
    # Multi-actuator KIG: never guess. Mapping is deliberately not inferred from AID order.
    mapping=load_json(MAPPING,{})
    key=(mapping.get(str(aid)) or {}).get('position_key') if isinstance(mapping,dict) else None
    return key if key in keys else None

def send_position_udp_for_aid(aid,value,source):
    key=mapped_position_key(aid)
    if not key:
        log(f'UDP SKIP -> HAP AID {aid} noch keinem VELUX-Aktor sicher zugeordnet ({source})')
        return False
    # Reuse existing sender without changing KIX behavior by temporarily using the resolved key.
    state=load_json(STATE,{})
    values=state.get('values',{}) if isinstance(state,dict) else {}
    allkeys=[k for k in values if str(k).startswith('module.') and str(k).endswith('.position')]
    if len(allkeys)==1:
        return send_position_udp(value,source)
    cfg=load_json(CONFIG,{})
    if not cfg.get('udp_enabled'): return False
    rules=cfg.get('udp_messages',{}) if isinstance(cfg.get('udp_messages',{}),dict) else {}
    rule=rules.get(key); enabled=bool(cfg.get('udp_auto_new',True)) if not isinstance(rule,dict) else bool(rule.get('enabled',True))
    if not enabled: return False
    target=udp_path(key if not isinstance(rule,dict) else (rule.get('name') or key))
    try:
        number=float(value); value=int(number) if number.is_integer() else number
    except (TypeError,ValueError): return False
    mode=str(cfg.get('udp_send_mode','always') or 'always').lower()
    cache=load_json(UDP_LAST,{}) if mode=='changed' else {}
    try: boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    except Exception: boot_id='unknown'
    last_sent=cache.get('values',{}) if isinstance(cache,dict) and cache.get('boot_id')==boot_id and isinstance(cache.get('values'),dict) else {}
    if mode=='changed' and last_sent.get(target)==value:
        log(f'UDP SKIP -> {target}={value} unverändert [Eventstream AID {aid} {source}]')
        return False
    msno=max(1,int(cfg.get('miniserver_no',1))); port=int(cfg.get('udp_port',7000)); prefix=slug(cfg.get('udp_prefix','velux'))
    helper=Path(__file__).resolve().parent/'loxberry_bridge.pl'
    r=subprocess.run([str(helper),'send',str(msno),str(port),prefix],input=json.dumps({target:value},ensure_ascii=False),capture_output=True,text=True,timeout=30)
    if r.returncode!=0: raise RuntimeError('LoxBerry UDP: '+(r.stderr.strip() or r.stdout.strip() or 'unbekannter Fehler'))
    if mode=='changed':
        last_sent[target]=value
        tmp=UDP_LAST.with_suffix('.json.tmp'); tmp.write_text(json.dumps({'boot_id':boot_id,'values':last_sent},indent=2,ensure_ascii=False),encoding='utf-8'); os.chmod(tmp,0o600); tmp.replace(UDP_LAST)
    log(f'UDP TX -> MS#{msno}:{port} {prefix}.{target}={value} [Eventstream AID {aid} {source}]')
    return True

def handle_event(cid, raw):
    EVENT_VALUES[cid]=raw
    meta=characteristic_index().get(str(cid),{})
    name=str(meta.get('name','')).strip().lower()
    try: aid=int(meta.get('aid',str(cid).split('.')[0]))
    except Exception: return
    # Dynamic per-accessory handling. No fixed 3.10/3.11/3.12 assumption.
    byname={}
    for k,c in characteristic_index().items():
        try:
            if int(c.get('aid'))==aid: byname[str(c.get('name','')).strip().lower()]=k
        except Exception: pass
    target_id=byname.get('position.target'); current_id=byname.get('position.current'); state_id=byname.get('position.state')
    # Generic Local-first path for every safely identifiable non-position value.
    # Unknown/ambiguous characteristics stay inventoried but are never guessed onto a cloud key.
    if not name.startswith('position.'):
        key=resolved_local_key(cid,name,aid)
        if key:
            value=normalize_local_value(name,raw)
            save_local_value(key,value,cid,name,aid)
            send_generic_udp(key,value,cid,name)
        return
    if name=='position.target':
        if str(raw).lower() not in ('null','none',''):
            learned=learn_mapping(aid,raw)
            send_position_udp_for_aid(aid,raw,'target' + ('-learned' if learned else ''))
        elif current_id and current_id in EVENT_VALUES:
            send_position_udp_for_aid(aid,EVENT_VALUES[current_id],'current-fallback')
    elif name=='position.state':
        try: state=int(float(raw))
        except (TypeError,ValueError): return
        if state==2 and current_id and current_id in EVENT_VALUES:
            send_position_udp_for_aid(aid,EVENT_VALUES[current_id],'current-final')
    elif name=='position.current':
        state=EVENT_VALUES.get(state_id) if state_id else None
        target=EVENT_VALUES.get(target_id) if target_id else None
        if str(target).lower() in ('null','none',''):
            send_position_udp_for_aid(aid,raw,'current-fallback')
        elif str(state) in ('2','2.0'):
            send_position_udp_for_aid(aid,raw,'current-final')

def run_once(ids):
    global CHILD
    cmd=[sys.executable,'-u','-m','homekit.get_events','-f',str(PAIR),'-a',ALIAS]
    for cid in ids: cmd += ['-c',cid]
    log('SUBSCRIBE -> '+', '.join(ids)); save(running=True,state='subscribing',characteristics=len(ids),error='')
    CHILD=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1)
    assert CHILD.stdout is not None
    for line in CHILD.stdout:
        if STOP: break
        line=line.strip()
        if not line: continue
        m=re.search(r'event for\s+(\d+\.\d+):\s*(.*)',line,re.I)
        if m:
            cid=m.group(1); raw=m.group(2)
            log('RECEIVE '+cid+' = '+raw); save(running=True,state='connected',last_event_at=int(time.time()),last_characteristic=cid,last_value=raw)
            try: handle_event(cid,raw)
            except Exception as e: log('UDP FEHLER -> '+str(e))
        else:
            log('HAP '+line); save(running=True,state='connected',last_hap_message=line[:500])
    if STOP and CHILD.poll() is None:
        try: CHILD.terminate(); CHILD.wait(timeout=5)
        except Exception:
            try: CHILD.kill()
            except: pass
    rc=CHILD.wait(); CHILD=None
    return rc

def main():
    PID.parent.mkdir(parents=True,exist_ok=True); PID.write_text(str(os.getpid()))
    try:
        ids=load_ids()
        if not ids: raise RuntimeError('Keine eventfähigen Characteristics gefunden. Zuerst Event-Characteristics lesen.')
        prepare_local_mappings()
        log('LISTENER START -> '+str(len(ids))+' Characteristics werden abonniert'); save(running=True,started_at=int(time.time()),characteristics=len(ids),mode='local-first',state='starting',error='')
        attempt=0
        while not STOP:
            attempt+=1
            try:
                rc=run_once(ids)
                if STOP: break
                msg='HomeKit Eventprozess beendet, Code '+str(rc)
            except Exception as e: msg=str(e)
            log('RECONNECT -> '+msg+'; neuer Versuch in 5 s'); save(running=True,state='reconnecting',error=msg,error_at=int(time.time()),reconnect_attempt=attempt)
            for _ in range(5):
                if STOP: break
                time.sleep(1)
        save(running=False,state='stopped',stopped_at=int(time.time()))
        log('LISTENER STOP')
    except Exception as e:
        log('FEHLER: '+str(e)); save(running=False,state='error',error=str(e),error_at=int(time.time()))
    finally:
        try: PID.unlink()
        except: pass
if __name__=='__main__': main()
