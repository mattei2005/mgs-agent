#!/usr/bin/env python3
"""GET-only authority, native top-level thumbnail and source investigation."""
import sys,json,hashlib,re,importlib.util,ssl
from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import urlsplit
sys.path.insert(0,'/root/mgs-agent/scripts')
from ares_campaign_v3 import target_start_revision as revision
from ares_campaign_v3.native_thumbnail_equivalence import _PinnedHTTPS,fetch_native,NATIVE
spec=importlib.util.spec_from_file_location('runner_image_supplement','/root/mgs-agent/scripts/ares-eggbev-target-clone.py')
assert spec is not None and spec.loader is not None
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
common,meta,sb,token=r.runtime()
home=Path('/root/mgs-agent/data/ares/meta-ads/audit/eggbev/target-clone/eggbev-pg23189-1571342489162489937');root=Path(__file__).resolve().parent
out={'at':datetime.now(timezone.utc).isoformat(),'meta_writes':0,'drive_writes':0,'results':[]}
def save(): (root/'supplement-get.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
def get(label,path,fields):
 code,v,_=meta.graph_get(path,token,{'fields':fields})
 # Errors contain documentation links, not signed data. Keep only sanitized error fields.
 if code!=200:
  e=v.get('error',{});row={'label':label,'http_status':code,'error':{k:re.sub(r'https?://\S+','[documentation URL]',str(e[k])) if k=='message' else e[k] for k in ['code','error_subcode','type','message'] if k in e}};out['results'].append(row);save();print(json.dumps(row,ensure_ascii=False),flush=True)
 return code,v
def download(label,url):
 result={'label':label,'url_sha256':hashlib.sha256(url.encode()).hexdigest()}
 try:
  if NATIVE.fullmatch(url):
   raw=fetch_native(url);result.update(http_status=200,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),image_signature=raw[:3]==b'\xff\xd8\xff')
  else:
   p=urlsplit(url)
   if p.scheme!='https' or not re.fullmatch(r'scontent-[a-z0-9-]+\.xx\.fbcdn\.net',p.netloc) or p.fragment:raise ValueError('nonapproved thumbnail endpoint')
   conn=_PinnedHTTPS(p.netloc,timeout=15,context=ssl.create_default_context())
   try:
    conn.request('GET',p.path+'?'+p.query,headers={'Accept':'image/*','Connection':'close'});resp=conn.getresponse();raw=resp.read(4*1024*1024+1)
    result.update(http_status=resp.status,content_type=resp.getheader('Content-Type'),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),image_signature=raw[:3]==b'\xff\xd8\xff')
    assert len(raw)<=4*1024*1024
   finally:conn.close()
 except Exception as e:result['safe_error']=type(e).__name__
 out['results'].append(result);save();print(json.dumps(result),flush=True)
ctx=revision.validate_local(home/'request.json',r.load(r.CONFIG),'7fb94557a6302e97bcc5239ad7f7758052555203f3ff15c360e1ffef55c5afba','1571376388437577861')
revision.live_authority(ctx,meta=meta,token=token)
out['authority']='fresh original thread/approval/ASAP/channel/actor/app validated';save()
q=r.load(home/'request.json');source=r.source_read(q,common,meta,token);old=r.load(home/'source-live.json')
out['source_comparison_unchanged']=r.source_comparison(source)==r.source_comparison(old)
if not out['source_comparison_unchanged']:
 from ares_campaign_v3.native_thumbnail_equivalence import compare
 out['source_thumbnail_equivalence']=compare(old,source,context={'request_id':q['request_id'],'approved_digest':'7fb94557a6302e97bcc5239ad7f7758052555203f3ff15c360e1ffef55c5afba','account_id':q['account_id'],'source_campaign_id':q['source_campaign_id_candidate']},normalize=r.source_comparison)
save()
for cid in ['1676402284181464','1433535772149643','1612556403313873']:
 code,v=get('creative:'+cid,cid,'id,thumbnail_url,image_hash,image_url,asset_feed_spec')
 if code==200:
  out['results'].append({'label':'creative_fields:'+cid,'fields_returned':list(v),'image_hash_present':'image_hash'in v,'image_url_present':'image_url'in v});save()
  if v.get('thumbnail_url'):download('creative_top_thumbnail:'+cid,v['thumbnail_url'])
  if cid=='1676402284181464':
   for vv in v['asset_feed_spec']['videos']:download('afs_thumbnail:'+vv['video_id'],vv['thumbnail_url'])
for vid in ['2807134573018239','1400003821960729','2595832870918472','2581693622310769']:
 code,v=get('video:'+vid,vid,'id,thumbnails{id,is_preferred,uri,width,height}')
 if code==200:
  for t in v.get('thumbnails',{}).get('data',[]):
   if t.get('is_preferred'):download('preferred_thumbnail:'+vid+':'+t['id'],t['uri'])
get('story_ad01','1355561690982225_122098583937552287','id')
# Smallest story GET differentiates field errors from object/token requirements.
get('story_control_ad02','1355561690982225_122098584051552287','id')
save()
