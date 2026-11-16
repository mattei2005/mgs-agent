"""Receipt-bound physical media repair; logical manifest/seals never rewritten."""
from pathlib import Path
from dataclasses import replace
from types import SimpleNamespace
import json,hashlib
ROOT=Path('/root/mgs-agent')
def digest(v):return hashlib.sha256(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def substitute(v,mapping):
 if isinstance(v,str):return mapping.get(v,v)
 if isinstance(v,list):return [substitute(x,mapping) for x in v]
 if isinstance(v,dict):return {k:substitute(x,mapping) for k,x in v.items()}
 return v

def admit(engine,bundle,record):
 p=getattr(engine,'_same_account_execution_authority',None) or {};route=p.get('route_receipt') or {}
 if not route or route.get('account_id')!=bundle.account_id:return
 relative=Path('data/ares/meta-ads/audit/eggbev/same-account')/p['request_id']/'execution/media-visibility-repair/materialization-receipt.json'
 if p.get('media_materialization_authorized')!=str(relative):return
 path=ROOT/relative
 if not path.exists():return
 r=json.loads(path.read_text());original=json.loads(Path(r['original_manifest_path']).read_text());candidate=Path(r['candidate_registry_path'])
 if (r.get('request_id')!=p['request_id'] or r.get('account_id')!=bundle.account_id or r.get('authority_message_id')!=route['authority_message_id']
     or r.get('original_manifest_digest')!=record['sealed_manifest_digest'] or digest(original)!=r['original_manifest_digest']
     or r.get('app_id')!=route['target_app_id'] or r.get('canonical_bytes_preserved') is not True or len(r.get('mapping',{}))!=30
     or hashlib.sha256(candidate.read_bytes()).hexdigest()!=r['candidate_registry_sha256']):raise ValueError('physical media repair receipt invalid')
 for c in bundle.campaigns:
  for ai,ad in enumerate(c.ads,1):
   slot=r['slots'][c.idempotency_key+':'+str(ai)]
   if digest(ad.creative_payload)!=slot['original_payload_digest'] or ad.media.checksum!=slot['checksum']:raise ValueError('physical media repair changed original payload/asset')
 record['media_materialization_receipt']={'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
 from .target_page_clone import _save
 _save()

def receipt(record):
 binding=record.get('media_materialization_receipt')
 if not binding:return None
 path=Path(binding['path'])
 if hashlib.sha256(path.read_bytes()).hexdigest()!=binding['sha256']:raise ValueError('physical media receipt drift')
 r=json.loads(path.read_text())
 if r['original_manifest_digest']!=record['sealed_manifest_digest']:raise ValueError('physical media seal mismatch')
 return r

def materialize(bundle,record):
 r=receipt(record)
 if not r:return bundle
 campaigns=[]
 for c in bundle.campaigns:
  if c.account_id!=r['account_id'] or c.mode!='clone_target_prestaged':raise ValueError('physical media account/mode mismatch')
  ads=[]
  for ai,ad in enumerate(c.ads,1):
   slot=r['slots'][c.idempotency_key+':'+str(ai)];payload=ad.creative_payload
   if digest(payload)==slot['original_payload_digest']:payload=substitute(payload,r['mapping'])
   elif digest(payload)!=slot['physical_payload_digest']:raise ValueError('physical creative drift')
   if digest(payload)!=slot['physical_payload_digest']:raise ValueError('physical creative derivation failed')
   media=replace(ad.media,vertical_video_id=r['mapping'].get(ad.media.vertical_video_id,ad.media.vertical_video_id),square_video_id=r['mapping'].get(ad.media.square_video_id,ad.media.square_video_id))
   ads.append(replace(ad,creative_payload=payload,media=media))
  campaigns.append(replace(c,ads=tuple(ads)))
 try:return replace(bundle,campaigns=tuple(campaigns))
 except TypeError:return SimpleNamespace(**{**vars(bundle),'campaigns':tuple(campaigns)})

def media_id(record,original):
 r=receipt(record)
 return r['mapping'].get(original,original) if r else original
