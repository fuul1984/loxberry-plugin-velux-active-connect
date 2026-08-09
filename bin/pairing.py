#!/usr/bin/env python3
from __future__ import annotations
import base64, socket, struct, time, uuid
from dataclasses import dataclass
try:
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import x25519
    from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
except ImportError as e:
    raise RuntimeError("Python-Modul 'cryptography' fehlt. Gateway-Kopplung benötigt python3-cryptography.") from e

FRAME_PING=0x0000; FRAME_PONG=0x0001; FRAME_CLOSE=0x0008; FRAME_SECURE=0x0200
FRAME_ECDH_REQUEST=0x0201; FRAME_ECDH_RESPONSE=0x0202
FRAME_END_TO_END_NONCE_REQUEST=0x020A; FRAME_END_TO_END_NONCE_RESPONSE=0x020B
FRAME_END_TO_END_CHALLENGE_REQUEST=0x020C; FRAME_END_TO_END_CHALLENGE_RESPONSE=0x020D
FRAME_END_TO_END_KEY_REQUEST=0x020E; FRAME_END_TO_END_KEY_RESPONSE=0x020F
NETCOM_PORT=25050

class VeluxPairingError(Exception): pass

@dataclass
class SigningKey:
    sign_key_id:str
    hash_sign_key:str

class Frame:
    def __init__(self,t,p): self.frame_type=t; self.payload=p

class NetcomSocket:
    def __init__(self,host,port,timeout):
        self.s=socket.create_connection((host,port),timeout=timeout); self.s.settimeout(timeout); self.buf=bytearray()
    def close(self): self.s.close()
    def send(self,b): self.s.sendall(b)
    def recv_frame(self):
        while len(self.buf)<4:self._recv()
        t,n=struct.unpack_from("<HH",self.buf); total=4+n
        while len(self.buf)<total:self._recv()
        raw=bytes(self.buf[:total]); del self.buf[:total]
        return Frame(t,raw[4:])
    def _recv(self):
        c=self.s.recv(4096)
        if not c: raise VeluxPairingError("Verbindung vom Gateway geschlossen")
        self.buf.extend(c)

class SecureContext:
    def __init__(self,key):
        self.aead=ChaCha20Poly1305(key); self.tx=bytearray(12); self.rx=bytearray(12)
    def encrypt_frame(self,frame):
        b=self.aead.encrypt(bytes(self.tx),frame,None); inc_nonce(self.tx); return pack(FRAME_SECURE,b)
    def decrypt(self,payload):
        b=self.aead.decrypt(bytes(self.rx),payload,None); inc_nonce(self.rx); return b

def pack(t,p=b""): return struct.pack("<HH",t,len(p))+p
def inc_nonce(n):
    for i in range(11,3,-1):
        if n[i]<255: n[i]+=1; return
        n[i]=0
    n[:]=b"\x00"*12
def expect(sock,types,label):
    while True:
        f=sock.recv_frame()
        if f.frame_type in types:return f
        if f.frame_type==FRAME_PING: sock.send(pack(FRAME_PONG)); continue
        raise VeluxPairingError(f"Unerwarteter Frame bei {label}: 0x{f.frame_type:04x}")
def secure_payload(sock,sec,etype,label):
    f=expect(sock,{FRAME_SECURE},label); raw=sec.decrypt(f.payload)
    if len(raw)<4: raise VeluxPairingError(f"{label}: Antwort zu kurz")
    t,n=struct.unpack_from("<HH",raw); p=raw[4:]
    if t!=etype or len(p)!=n: raise VeluxPairingError(f"{label}: ungültige Antwort")
    return p
def ecdh(sock):
    sock.send(pack(FRAME_PING)); pong=expect(sock,{FRAME_PONG},"Ping")
    priv=x25519.X25519PrivateKey.generate()
    pub=priv.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw)
    sock.send(pack(FRAME_ECDH_REQUEST,b"\x01"+pub))
    gp=expect(sock,{FRAME_ECDH_RESPONSE},"ECDH").payload
    if len(gp)==33 and gp[0] in (0,1): gp=gp[1:]
    if len(gp)!=32: raise VeluxPairingError("ECDH Public Key hat nicht 32 Bytes")
    secret=priv.exchange(x25519.X25519PublicKey.from_public_bytes(gp))
    d=hashes.Hash(hashes.SHA512()); d.update(secret)
    return SecureContext(d.finalize()[:32])
def request_key(host,port=NETCOM_PORT,timeout=10):
    kid=uuid.uuid4().bytes; sock=NetcomSocket(host,port,timeout)
    try:
        sec=ecdh(sock)
        sock.send(sec.encrypt_frame(pack(FRAME_END_TO_END_KEY_REQUEST,b"\x00"+kid)))
        p=secure_payload(sock,sec,FRAME_END_TO_END_KEY_RESPONSE,"Key")
        if not p or p[0]!=0: raise VeluxPairingError(f"Gateway lehnt Schlüssel ab (Code {p[0] if p else '?'})")
        if len(p)!=33: raise VeluxPairingError("Unerwartete Schlüssellänge")
        key=p[1:]
        sock.send(sec.encrypt_frame(pack(FRAME_END_TO_END_NONCE_REQUEST,b"\x00")))
        nonce=secure_payload(sock,sec,FRAME_END_TO_END_NONCE_RESPONSE,"Nonce")
        d=hashes.Hash(hashes.SHA512()); d.update(kid); d.update(key); d.update(nonce)
        sock.send(sec.encrypt_frame(pack(FRAME_END_TO_END_CHALLENGE_REQUEST,kid+d.finalize())))
        r=secure_payload(sock,sec,FRAME_END_TO_END_CHALLENGE_RESPONSE,"Challenge")
        if not r or r[0]!=0: raise VeluxPairingError(f"Challenge fehlgeschlagen (Code {r[0] if r else '?'})")
        sock.send(sec.encrypt_frame(pack(FRAME_CLOSE)))
    finally: sock.close()
    enc=lambda b: base64.urlsafe_b64encode(b).decode("ascii")
    return SigningKey(enc(kid),enc(key))

def retrieve_signing_key(host,timeout=40,socket_timeout=10):
    end=time.monotonic()+timeout; last=None
    while time.monotonic()<end:
        try:
            with socket.create_connection((host,NETCOM_PORT),timeout=.5): pass
            return request_key(host,NETCOM_PORT,socket_timeout)
        except Exception as e:
            last=e; time.sleep(1)
    raise VeluxPairingError(str(last) if last else f"Port {NETCOM_PORT} wurde nicht geöffnet")
