#!/usr/bin/env python3
import argparse,json,os,subprocess,sys,time
from pathlib import Path
CFG=Path(os.environ.get('LBPCONFIGDIR','/opt/loxberry/config/plugins/veluxactive'))
DATA=Path(os.environ.get('LBPDATADIR','/opt/loxberry/data/plugins/veluxactive'))
PAIR=CFG/'homekit_pairing.json'; CHARS=DATA/'event_characteristics.json'; ALIAS='velux_events'
sys.path.insert(0,str(Path(__file__).resolve().parent))
from logutil import log

def load(p,d):
    try:return json.loads(p.read_text(encoding='utf-8'))
    except:return d

def find_target(aid=None):
    chars=load(CHARS,[])
    hits=[]
    for c in chars if isinstance(chars,list) else []:
        name=str(c.get('name','')).strip().lower()
        perms=[x.strip().lower() for x in str(c.get('permissions','')).split(',')]
        if name=='position.target' and 'pw' in perms:
            if aid is None or int(c.get('aid',-1))==int(aid):
                hits.append(c)
    if not hits:
        raise RuntimeError('Keine beschreibbare position.target-Characteristic gefunden. Eventstream neu initialisieren.')
    if len(hits)>1:
        raise RuntimeError('Mehrere beschreibbare position.target-Characteristics gefunden; Ziel-AID ist nicht eindeutig.')
    c=hits[0]
    return int(c['aid']),int(c['iid'])

def write_position(value, aid=None):
    if not PAIR.exists(): raise RuntimeError('HAP/Eventstream ist nicht gekoppelt.')
    try:v=int(value)
    except: raise RuntimeError('Position muss eine ganze Zahl von 0 bis 100 sein.')
    if not 0<=v<=100: raise RuntimeError('Position muss zwischen 0 und 100 liegen.')
    aid,iid=find_target(aid); cid=f'{aid}.{iid}'
    log(f'HAP CONTROL -> WRITE {cid} position.target={v}')
    r=subprocess.run([sys.executable,'-m','homekit.put_characteristic','-f',str(PAIR),'-a',ALIAS,'-c',cid,str(v)],capture_output=True,text=True,timeout=30)
    if r.returncode:
        err=(r.stderr.strip() or r.stdout.strip() or f'Exit {r.returncode}')
        log(f'HAP CONTROL FEHLER -> {cid} position.target={v}: {err}')
        raise RuntimeError(err)
    out={'ok':True,'characteristic':cid,'name':'position.target','value':v,'time':int(time.time())}
    (DATA/'hap_control_status.json').write_text(json.dumps(out,indent=2,ensure_ascii=False),encoding='utf-8')
    log(f'HAP CONTROL OK -> {cid} position.target={v}; warte auf Eventstream-Rückmeldung')
    return out

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--position',required=True); a=ap.parse_args()
    try: print(json.dumps(write_position(a.position),ensure_ascii=False))
    except Exception as e:
        print(json.dumps({'ok':False,'error':str(e)},ensure_ascii=False)); sys.exit(1)
