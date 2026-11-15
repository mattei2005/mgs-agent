#!/usr/bin/env python3
"""Exact request AD01 image investigation. GET-only, projected output."""
import sys,json,hashlib,re,importlib.util
from pathlib import Path
from datetime import datetime,timezone
sys.path.insert(0,'/root/mgs-agent/scripts')
ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('image_diagnostic_runner','/root/mgs-agent/scripts/ares-eggbev-target-clone.py')
assert spec is not None and spec.loader is not None
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
common,meta,sb,token=r.runtime()
# Prevent accidental mutation through this diagnostic runtime.
def forbidden(*a,**k):raise RuntimeError('GET-only maintenance forbids writes')
for name in ['graph_post','graph_delete','graph_batch']: 
 if hasattr(meta,name):setattr(meta,name,forbidden)
results=[]
def project(x):
 if isinstance(x,dict):return {k:project(v) for k,v in x.items() if k not in {'access_token','paging','fbtrace_id','token','appsecret_proof'}}
 if isinstance(x,list):return [project(v) for v in x]
 if isinstance(x,str) and ('https://' in x or 'http://' in x):
  # Signed URLs never persist. Their byte identity remains comparable.
  return {'redacted_url_sha256':hashlib.sha256(x.encode()).hexdigest()}
 return x
def save():
 p=ROOT/'get-diagnostic.json';p.write_text(json.dumps({'at':datetime.now(timezone.utc).isoformat(),'remote_writes':0,'results':results},ensure_ascii=False,indent=2)+'\n')
def get(label,path,fields):
 code,v,h=meta.graph_get(path,token,{'fields':fields})
 results.append({'label':label,'path':path,'fields':fields,'http_status':code,'body':project(v)});save()
 print(label,code, json.dumps(project(v),ensure_ascii=False)[:2400],flush=True)
 return code,v
code,ident,_=meta.graph_get_credential_metadata(r.ACCOUNT,token)
sc,issuer,_=meta.graph_get_credential_metadata(r.ACCOUNT,token,inspect_token=True)
i=issuer.get('data',{})
assert code==sc==200 and ident.get('id')=='122147293515218951' and str(i.get('app_id'))=='953171080682697' and str(i.get('user_id'))=='122147293515218951' and i.get('type')=='USER' and i.get('is_valid') is True
results.append({'label':'identity','http_status':200,'actor_id':ident['id'],'app_id':str(i['app_id']),'type':i['type']});save()
for ad in ['120251246303620629','120251246303850629']:
 get('ad:'+ad,ad,'id,status,configured_status,effective_status,issues_info,updated_time,adset_id,source_ad_id,creative{id}')
for creative in ['1676402284181464','1433535772149643','1612556403313873']:
 get('creative:'+creative,creative,'id,status,object_type,image_hash,image_url,thumbnail_url,object_story_id,effective_object_story_id,object_story_spec,asset_feed_spec,url_tags,degrees_of_freedom_spec,contextual_multi_ads')
for video in ['2807134573018239','1400003821960729','2595832870918472','2581693622310769']:
 get('video:'+video,video,'id,status,picture,thumbnails{id,is_preferred,uri,width,height}')
for story in ['1355561690982225_122098583937552287','1355561690982225_122098584051552287']:
 get('story:'+story,story,'id,is_published,message,attachments{media,type,target,subattachments},full_picture')
get('parent','120251246081230629','id,status,daily_budget')
