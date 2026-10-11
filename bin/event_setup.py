#!/usr/bin/env python3
import argparse,json,os,re,socket,subprocess,sys,time
from pathlib import Path
CFG=Path(os.environ.get('LBPCONFIGDIR','/opt/loxberry/config/plugins/veluxactive'))
DATA=Path(os.environ.get('LBPDATADIR','/opt/loxberry/data/plugins/veluxactive'))
PAIR=CFG/'homekit_pairing.json'; STATUS=DATA/'event_status.json'
ALIAS='velux_events'
def run(args,timeout=45):
    return subprocess.run([sys.executable,'-m','homekit']+args,capture_output=True,text=True,timeout=timeout)
def _discover_zeroconf(preferred_host=''):
    """Read _hap._tcp service records directly. The HAP port always comes from mDNS."""
    try:
        import socket
        from zeroconf import Zeroconf, ServiceBrowser, ServiceListener
    except Exception as e:
        return [], 'Zeroconf nicht verfügbar: '+str(e)
    found=[]
    class Listener(ServiceListener):
        def add_service(self, zc, stype, name):
            try:
                info=zc.get_service_info(stype,name,timeout=2500)
                if not info: return
                props={}
                for k,v in (info.properties or {}).items():
                    try: kk=k.decode('utf-8','replace') if isinstance(k,bytes) else str(k)
                    except Exception: kk=str(k)
                    try: vv=v.decode('utf-8','replace') if isinstance(v,bytes) else str(v)
                    except Exception: vv=str(v)
                    props[kk]=vv
                addrs=[]
                try: addrs=info.parsed_addresses()
                except Exception:
                    for raw in getattr(info,'addresses',[]) or []:
                        try: addrs.append(socket.inet_ntoa(raw))
                        except Exception: pass
                host=(preferred_host if preferred_host and preferred_host in addrs else (addrs[0] if addrs else (getattr(info,'server','') or '').rstrip('.')))
                found.append({'name':name.rstrip('.'),'device_id':props.get('id',''),'host':host,'addresses':addrs,'port':int(info.port),'model':props.get('md',''),'protocol':props.get('pv',''),'source':'_hap._tcp'})
            except Exception: pass
        def update_service(self, zc, stype, name): self.add_service(zc,stype,name)
        def remove_service(self, zc, stype, name): pass
    zc=Zeroconf()
    try:
        browser=ServiceBrowser(zc,'_hap._tcp.local.',Listener())
        time.sleep(8)
        try: browser.cancel()
        except Exception: pass
    finally:
        zc.close()
    # de-duplicate service announcements
    uniq={}
    for x in found: uniq[(x.get('device_id'),x.get('host'),x.get('port'))]=x
    return list(uniq.values()), ''

def _discover_cli():
    r=subprocess.run([sys.executable,'-m','homekit.discover','-t','8'],capture_output=True,text=True,timeout=15)
    if r.returncode: return [], (r.stderr.strip() or r.stdout.strip())
    found=[]
    # Parse by Name boundaries instead of relying on blank lines; homekit_python output can vary.
    blocks=re.split(r'(?=^Name:\s*)',r.stdout,flags=re.M)
    for b in blocks:
        did=re.search(r'Device ID \(id\):\s*(.+)',b)
        url=re.search(r'Url:\s*[^:]+://([^:/\s]+):(\d+)',b)
        name=re.search(r'^Name:\s*(.+)',b,re.M)
        model=re.search(r'Model Name \(md\):\s*(.+)',b)
        pv=re.search(r'Protocol Version \(pv\):\s*(.+)',b)
        if did and url:
            found.append({'name':name.group(1).strip() if name else 'HAP Gateway','device_id':did.group(1).strip(),'host':url.group(1),'addresses':[url.group(1)],'port':int(url.group(2)),'model':model.group(1).strip() if model else '','protocol':pv.group(1).strip() if pv else '','source':'homekit.discover'})
    return found, ''

def discover(preferred_host=''):
    found,err=_discover_zeroconf(preferred_host)
    if not found:
        found,err2=_discover_cli(); err=err or err2
    if not found:
        extra=(' Details: '+err) if err else ''
        raise RuntimeError('Kein HAP-Service (_hap._tcp) gefunden.'+extra)
    # Existing paired VELUX gateway IP wins. We never guess a port: it must be in the HAP record.
    if preferred_host:
        matches=[x for x in found if preferred_host==x.get('host') or preferred_host in x.get('addresses',[])]
        if matches: return matches[0]
        raise RuntimeError('HAP-Services gefunden, aber keiner gehört zur bekannten Gateway-IP '+preferred_host+'. Gefunden: '+', '.join('%s:%s'%(x.get('host','?'),x.get('port','?')) for x in found))
    velux=[x for x in found if 'VELUX' in ('%s %s'%(x.get('name',''),x.get('model',''))).upper()]
    if len(velux)==1: return velux[0]
    if len(found)==1: return found[0]
    if velux: return velux[0]
    raise RuntimeError('Mehrere HAP-Geräte gefunden; ohne bekannte Gateway-IP ist keine eindeutige VELUX-Zuordnung möglich.')
def probe(host,port):
    """Read-only direct TCP/HAP diagnostic. Does not pair, identify or control the accessory."""
    host=(host or '').strip()
    if not host: raise RuntimeError('Bekannte Gateway-IP fehlt.')
    try: port=int(port)
    except Exception: raise RuntimeError('HAP-Port fehlt oder ist ungültig.')
    if not (1 <= port <= 65535): raise RuntimeError('HAP-Port ist ungültig.')
    started=time.time()
    try:
        with socket.create_connection((host,port),timeout=3) as s:
            s.settimeout(3)
            # GET /accessories is read-only. An unpaired HAP accessory normally rejects it,
            # but an HAP-formatted HTTP response proves that the endpoint speaks HAP/HTTP.
            req=(f'GET /accessories HTTP/1.1\r\nHost: {host}:{port}\r\nConnection: close\r\n\r\n').encode('ascii')
            s.sendall(req)
            data=b''
            try:
                while len(data)<4096:
                    chunk=s.recv(1024)
                    if not chunk: break
                    data+=chunk
                    if b'\r\n\r\n' in data: break
            except socket.timeout:
                pass
    except Exception as e:
        raise RuntimeError(f'Direkte TCP-Verbindung zu {host}:{port} fehlgeschlagen: {e}')
    text=data.decode('iso-8859-1','replace')
    first=text.splitlines()[0] if text.splitlines() else ''
    hapish=('HTTP/1.1' in first or 'HTTP/1.0' in first or 'application/hap+json' in text.lower())
    out={'host':host,'port':port,'tcp':True,'hap_http_response':bool(hapish),'response':first or '(keine HTTP-Statuszeile)','elapsed_ms':int((time.time()-started)*1000),'source':'direct-diagnostic'}
    DATA.mkdir(parents=True,exist_ok=True)
    (DATA/'event_probe.json').write_text(json.dumps(out,indent=2,ensure_ascii=False),encoding='utf-8')
    return out

def pair(code,preferred_host='',preferred_port=''):
    """Pair directly with the verified KIX/KIG HAP endpoint.

    homekit_python normally uses accessory_id only to resolve IP/port via Bonjour
    before Pair-Setup. In routed/VLAN setups Bonjour may be unavailable although
    the HAP endpoint is reachable. We replace only that lookup with the explicit,
    previously diagnosed endpoint. The accessory's real pairing identifier and
    public key are still obtained and cryptographically verified during Pair-Setup.
    """
    host=(preferred_host or '').strip()
    if not host:
        raise RuntimeError('Bekannte Gateway-IP fehlt.')
    try: port=int(preferred_port)
    except Exception: raise RuntimeError('HAP-Port fehlt oder ist ungültig.')
    if not (1 <= port <= 65535): raise RuntimeError('HAP-Port ist ungültig.')

    # Safety guard: require the endpoint to answer as HAP/HTTP before sending
    # any Pair-Setup data. This also prevents falling back to another mDNS device.
    pr=probe(host,port)
    if not pr.get('hap_http_response'):
        raise RuntimeError('Der direkte Gateway-Endpunkt antwortet nicht als HAP/HTTP.')

    digits=re.sub(r'\D','',code)
    if len(digits)!=8: raise RuntimeError('HomeKit-Code muss 8 Ziffern enthalten.')
    pin=f'{digits[:3]}-{digits[3:5]}-{digits[5:]}'

    DATA.mkdir(parents=True,exist_ok=True); CFG.mkdir(parents=True,exist_ok=True)
    try:
        import homekit.controller.controller as hc
        from homekit.controller import Controller
        try:
            from homekit.controller.controller import PairingAuth
        except Exception:
            PairingAuth=None
    except Exception as e:
        raise RuntimeError('homekit_python ist nicht verfügbar: '+str(e))

    controller=Controller()
    if PAIR.exists():
        try:
            controller.load_data(str(PAIR))
        except Exception:
            # An empty/old diagnostic file must not make us pair a wrong device.
            pass
    if ALIAS in controller.get_pairings():
        raise RuntimeError('Eventstream ist bereits gekoppelt. Bitte zuerst die vorhandene Kopplung verwenden.')

    # Preserve homekit_python's complete cryptographic Pair-Setup implementation.
    # homekit_python 0.19.0: Controller.start_pairing() resolves
    # find_device_ip_and_port() from its function globals. We replace only this
    # Bonjour lookup for the duration of Pair-Setup; all cryptography and HAP
    # protocol handling remain untouched in homekit_python.
    pairing_globals=Controller.start_pairing.__globals__
    resolver_name='find_device_ip_and_port'
    if resolver_name not in pairing_globals:
        raise RuntimeError('homekit_python 0.19.0: find_device_ip_and_port wurde nicht gefunden.')
    original_resolver=pairing_globals[resolver_name]
    def direct_resolver(_accessory_id):
        return {'ip':host,'port':port}
    pairing_globals[resolver_name]=direct_resolver
    try:
        if PairingAuth is not None:
            controller.perform_pairing(ALIAS,'DIRECT-ENDPOINT',pin,PairingAuth.Auto)
        else:
            controller.perform_pairing(ALIAS,'DIRECT-ENDPOINT',pin)
        controller.save_data(str(PAIR))
    except Exception as e:
        raise RuntimeError('Direktes HAP-Pairing fehlgeschlagen: '+str(e))
    finally:
        pairing_globals[resolver_name]=original_resolver
        try: controller.shutdown()
        except Exception: pass

    # Read back the actual identifier learned from the accessory during Pair-Setup.
    actual_id=''
    try:
        pdata=json.loads(PAIR.read_text(encoding='utf-8'))
        entry=pdata.get(ALIAS,{})
        actual_id=entry.get('AccessoryPairingID','')
    except Exception: pass
    d={'name':'VELUX Gateway','device_id':actual_id,'host':host,'addresses':[host],
       'port':port,'model':'VELUX Gateway','protocol':'HAP IP','source':'direct-pairing'}
    st={'paired':True,'gateway':d,'paired_at':int(time.time()),'mode':'diagnostic-direct'}
    STATUS.write_text(json.dumps(st,indent=2,ensure_ascii=False),encoding='utf-8')
    return st

def accessories():
    r=subprocess.run([sys.executable,'-m','homekit.get_accessories','-f',str(PAIR),'-a',ALIAS,'-o','compact'],capture_output=True,text=True,timeout=45)
    if r.returncode: raise RuntimeError(r.stderr.strip() or r.stdout.strip())
    chars=[]
    metadata=[]
    raw_lines=[]
    # Keep identification characteristics as well as event characteristics.
    # KIG300 can expose several window actuators; their HAP AIDs must never be
    # assigned to cloud devices by ordering or guesswork.
    meta_names={
        'name','configured-name','manufacturer','model','serial-number',
        'firmware-revision','hardware-revision','accessory-flags'
    }
    for line in r.stdout.splitlines():
        if line.strip(): raw_lines.append(line.rstrip())
        m=re.match(r'\s*(\d+)\.(\d+):\s*(.*?)\s*\(([^)]*)\)\s*>(.*?)<\s*\[([^]]*)\]',line)
        if not m:
            continue
        aid=int(m.group(1)); iid=int(m.group(2))
        value=m.group(3).strip(); ctype=m.group(4).strip(); name=m.group(5).strip()
        perms=[x.strip() for x in m.group(6).split(',') if x.strip()]
        entry={
            'id':f'{aid}.{iid}', 'aid':aid, 'iid':iid,
            'value':value, 'type':ctype, 'name':name,
            'permissions':', '.join(perms), 'raw':line.strip()
        }
        lname=name.lower().replace('_','-').replace(' ','-')
        if lname in meta_names or any(k in lname for k in ('serial','manufacturer','model','configured-name','firmware','hardware')):
            metadata.append(entry.copy())
        if 'ev' in perms:
            chars.append(entry)
    DATA.mkdir(parents=True,exist_ok=True)
    (DATA/'event_characteristics.json').write_text(json.dumps(chars,indent=2,ensure_ascii=False),encoding='utf-8')
    (DATA/'event_accessory_metadata.json').write_text(json.dumps(metadata,indent=2,ensure_ascii=False),encoding='utf-8')
    (DATA/'event_accessories_compact.txt').write_text('\n'.join(raw_lines)+'\n',encoding='utf-8')
    # Same information in the normal plugin log so a remote test can be diagnosed
    # without relying on the CGI rendering. Never log pairing secrets.
    try:
        from logutil import log
        log(f'EVENT SCAN -> {len(chars)} eventfähige Characteristic(s), {len(metadata)} Identifikations-Characteristic(s)')
        for c in metadata:
            log('EVENT ACCESSORY META -> AID={aid} IID={iid} | {name}={value} | type={type} | perms={permissions}'.format(**c))
        for c in chars:
            log('EVENT CHARACTERISTIC -> AID={aid} IID={iid} | {name} | type={type} | value={value} | perms={permissions}'.format(**c))
    except Exception:
        pass
    return chars
if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('action',choices=['discover','probe','pair','accessories']); ap.add_argument('--code',default=''); ap.add_argument('--host',default=''); ap.add_argument('--port',default=''); a=ap.parse_args()
    try:
        out=discover(a.host) if a.action=='discover' else probe(a.host,a.port) if a.action=='probe' else pair(a.code,a.host,a.port) if a.action=='pair' else accessories(); print(json.dumps(out,ensure_ascii=False))
    except Exception as e: print(json.dumps({'error':str(e)},ensure_ascii=False)); sys.exit(1)
