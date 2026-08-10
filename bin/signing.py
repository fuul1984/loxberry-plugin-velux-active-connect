from __future__ import annotations
import base64,hashlib,hmac,time
def decode_key(v):
    v=v.strip().replace("-","+").replace("_","/"); v+="="*(-len(v)%4); return base64.b64decode(v,validate=True)
def compute_hash(key,position,timestamp,nonce,device_id):
    msg=f"target_position{position}{timestamp}{nonce}{device_id}".encode()
    d=hmac.new(decode_key(key),msg,hashlib.sha512).digest()
    return base64.b64encode(d).decode().replace("+","-").replace("/","_")
def build_signed_module(module_id,position,bridge_id,sign_key_id,hash_sign_key,timestamp=None,nonce=0):
    timestamp=int(time.time()) if timestamp is None else int(timestamp)
    return {"id":module_id,"nonce":nonce,"bridge":bridge_id,"sign_key_id":sign_key_id,
            "target_position":int(position),"force":True,
            "hash_target_position":compute_hash(hash_sign_key,int(position),timestamp,nonce,module_id),
            "timestamp":timestamp}

def compute_named_hash(key,item_name,value,timestamp,nonce,device_id):
    msg=f"{item_name}{value}{int(timestamp)}{int(nonce)}{device_id}".encode()
    d=hmac.new(decode_key(key),msg,hashlib.sha512).digest()
    return base64.b64encode(d).decode().replace("+","-").replace("/","_")

def build_signed_scenario(gateway_id,scenario,sign_key_id,hash_sign_key,timestamp=None,nonce=0):
    timestamp=int(time.time()) if timestamp is None else int(timestamp)
    scenario=str(scenario)
    return {
        "id":gateway_id,
        "nonce":int(nonce),
        "sign_key_id":sign_key_id,
        "scenario":scenario,
        "hash_scenario":compute_named_hash(hash_sign_key,"scenario",scenario,timestamp,nonce,gateway_id),
        "timestamp":timestamp
    }
