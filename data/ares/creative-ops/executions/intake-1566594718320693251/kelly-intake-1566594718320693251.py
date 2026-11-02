import sys,json,time,hashlib,subprocess,re,fcntl,importlib.util,os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0,'/root/mgs-agent/scripts')
import ares_archive_bridge as b, ares_archive_locations as loc, ares_autonomous_intake as intake
from PIL import Image,ImageDraw
T='1566594718320693251';OP='SHEIN_US_EN';ROOT='1ARBvLammWUHuAclNmcriwkkgeedKryBd';REQUESTER='1291113428982693940'
E=b.BASE/'data/ares/creative-ops/executions'/('intake-'+T);W=Path('/root/.hermes/profiles/ares/cache/scratch')/('media-'+T)
E.mkdir(parents=True,exist_ok=True);W.mkdir(parents=True,exist_ok=True)
def save(n,v):b.atomic_json(E/n,v)
def load(n):return b.read_json(E/n)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def rows():return [json.loads(x) for x in (b.BASE/'data/ares/creative-ops/inventory/assets.jsonl').read_text().splitlines() if x.strip()]
def selected(d):
 out=[]
 for r in d.listing(ROOT):
  if r['mimeType'].startswith('image/'):
   m=d.meta(r['id'])
   if m['createdTime'].startswith('2026-11-01') and 'US_SHEIN_EN_' in m['name'] and ' - K.' in m['name']:out.append(m)
 return sorted(out,key=lambda r:int(r['name'].split('_')[0]))
def prepare():
 d=b.Drive();polls=[]
 for i in range(3):
  a=selected(d);f=[[r['id'],r['name'],r['size']] for r in a];polls.append({'at':b.now_iso(),'set':f});print('stability',i+1,len(a),flush=True)
  if i<2:time.sleep(20)
 assert polls[0]['set']==polls[1]['set']==polls[2]['set'] and len(a)==21
 save('stability.json',polls)
 ids={r['id'] for r in a};assert not any(r.get('source_drive_id') in ids for r in rows())
 for r in a:intake.assert_source_writer(r['id'])
 def one(ir):
  i,r=ir;p=W/(f'{i:02}.jpg');p.write_bytes(d.raw(r['id']));assert len(p.read_bytes())==int(r['size']) and hashlib.md5(p.read_bytes()).hexdigest()==r['md5Checksum']
  im=Image.open(p);im.load();assert im.format=='JPEG';r.update(index=i,raw_path=str(p),raw_sha256=sha(p),width=im.width,height=im.height,real_format=im.format,format='IMG',pixel_sha256=hashlib.sha256(im.tobytes()).hexdigest());return r
 a=list(ThreadPoolExecutor(max_workers=4).map(one,enumerate(a,1)));save('sources.json',a)
 for start in [0,7,14]:
  sheet=Image.new('RGB',(7*240,480),'white');draw=ImageDraw.Draw(sheet)
  for j,r in enumerate(a[start:start+7]):
   im=Image.open(r['raw_path']);im.thumbnail((234,430));sheet.paste(im,(j*240+(240-im.width)//2,35));draw.text((j*240+8,10),f"#{r['index']} / {r['name'].split(' - ')[0]}",fill='black')
  path=W/f'review-{start+1:02}.jpg';sheet.save(path,quality=94);print('REVIEW',path,flush=True)
 print('prepared',len(a),flush=True)
def plan():
 a=load('sources.json');d=b.Drive();inventory=rows();ready=loc.stock_folder_for_path(d,[OP,'IMG','01_READY']);legacy=loc.stock_folder_for_path(d,[OP,'IMG','99_LEGACY'])
 occupied={r['name'] for r in d.listing(ready)}|{r.get('canonical_filename') for r in inventory if r.get('operation')==OP};occupied.discard(None)
 baby={1,5,6,7,10,11,12,13,16,18};items=[]
 for r in a:
  angle='FREE_BABY_TEES' if r['index'] in baby else 'FREE_PLUS_SIZE_OVERSIZED_HOODIES';r.update(angle=angle,human=False,p_orient='NV',visual_evidence=f"Reviewed original image #{r['index']}: English headline {'FREE Baby Tees!' if r['index'] in baby else 'FREE plus-size, oversized hoodies!'}; unworn clothing flat lay; no people or represented body parts; intact and legible.")
  p=W/(f"{r['index']:02}-clean.jpg")
  if not p.exists():subprocess.run([str(b.BASE/'scripts/clean-creative-metadata.sh'),'clean',r['raw_path'],'--out',str(p),'--agent','ares'],check=True,capture_output=True,text=True,timeout=180)
  v=subprocess.run([str(b.BASE/'scripts/clean-creative-metadata.sh'),'verify',str(p),'--json'],check=True,capture_output=True,text=True,timeout=90);assert json.loads(v.stdout)['clean'] is True
  im=Image.open(p);im.load();assert im.size==(r['width'],r['height'])
  r.update(clean_path=str(p),clean_sha256=sha(p),clean_md5=hashlib.md5(p.read_bytes()).hexdigest(),clean_size=p.stat().st_size,metadata_clean=True)
  matches=[x for x in inventory if r['raw_sha256'] in [x.get('original_checksum'),x.get('clean_checksum')] or r['clean_sha256'] in [x.get('original_checksum'),x.get('clean_checksum')]]
  assert not matches,('EXISTING_LINEAGE_RECONCILE_REQUIRED',r['index'])
  duplicates=[x for x in items if x['clean_sha256']==r['clean_sha256'] or x['raw_sha256']==r['raw_sha256']]
  if duplicates:
   first=duplicates[0];r.update(disposition='duplicate',duplicate_of=first['id'],final_name=first['final_name'],variant=first['variant'],asset_id=first['asset_id'])
  else:
   prefix=f'SHEIN_US_EN_IMG_{angle}_NV_';numbers=[int(m.group(1)) for n in occupied if (m:=re.fullmatch(re.escape(prefix)+r'(\d{3})\.[^.]+',n))];variant=max(numbers,default=0)+1;assert variant<=999
   name=prefix+f'{variant:03}.jpg';assert name not in occupied;occupied.add(name);r.update(disposition='new',variant=f'{variant:03}',final_name=name,asset_id='asset_'+hashlib.sha256((T+':'+r['id']).encode()).hexdigest()[:20])
  items.append(dict(r));print('planned',r['index'],r['disposition'],r['final_name'],flush=True)
 save('plan.json',{'schema':'mgs.manual.intake.plan.v1','thread_id':T,'operation':OP,'manager':'Kelly','source_parent':ROOT,'expected_count':len(a),'unique_count':len({r['asset_id'] for r in items}),'duplicate_count':sum(r['disposition']=='duplicate' for r in items),'planned_at':b.now_iso(),'dry_run_remote_writes':0,'locations':{'stock_ready':ready,'stock_legacy':legacy},'items':items})
 # sources contain only original snapshots, while plan additionally carries treatment and naming.
 for start in [0,7,14]:
  sheet=Image.new('RGB',(7*240,480),'white');draw=ImageDraw.Draw(sheet)
  for j,r in enumerate(items[start:start+7]):
   im=Image.open(r['clean_path']);im.thumbnail((234,430));sheet.paste(im,(j*240+(240-im.width)//2,35));draw.text((j*240+8,10),f"#{r['index']} CLEAN",fill='black')
  sheet.save(W/f'clean-review-{start+1:02}.jpg',quality=94)
 print('PLAN',len(a),'unique',len({r['asset_id'] for r in items}),'duplicates',sum(r['disposition']=='duplicate' for r in items),flush=True)
def execute():
 spec=importlib.util.spec_from_file_location('cp',str(b.BASE/'scripts/ares-execute-creative-copy-clean.py'));cp=importlib.util.module_from_spec(spec);spec.loader.exec_module(cp)
 d=b.Drive(True);c=cp.Drive(d.token);plan=load('plan.json');state=load('state.json') or {'phase':'execute','items':{}}
 with (E/'writer.lock').open('a+') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  loc.verify_staging_root(d);loc.verify_stock_root(d);root=d.api('GET','drives/'+b.SOURCE_DRIVE,{'fields':'id,name'});assert root['name']=='MGS-AGENTS'
  for r in plan['items']:
   if r['disposition']=='duplicate':continue
   intake.assert_source_writer(r['id']);assert sha(r['raw_path'])==r['raw_sha256'] and sha(r['clean_path'])==r['clean_sha256']
  ready=c.ensure_path('MGS-AGENTS/CRIATIVOS/'+OP+'/IMG/01_READY');legacy=c.ensure_path('MGS-AGENTS/CRIATIVOS/'+OP+'/IMG/99_LEGACY');state.update(ready_parent=ready,legacy_parent=legacy);save('state.json',state)
  for r in plan['items']:
   if r['disposition']=='duplicate':continue
   ent=state['items'].setdefault(r['id'],{})
   if all(ent.get(k) for k in ['destination_verified','legacy_verified','inventory_verified']):continue
   if not ent.get('dest_id'):
    possible=[m for m in d.listing(ready) if m['name']==r['final_name']]
    if possible:
     assert len(possible)==1 and hashlib.sha256(d.raw(possible[0]['id'])).hexdigest()==r['clean_sha256'];ent['dest_id']=possible[0]['id']
    else:
     ent['upload_intent_at']=b.now_iso();save('state.json',state);ent['dest_id']=c.upload_resumable(ready,r['final_name'],Path(r['clean_path']),r['mimeType'])
    save('state.json',state)
   fid=ent['dest_id'];m=d.meta(fid);assert m['parents']==[ready] and m['name']==r['final_name'] and m['driveId']==b.SOURCE_DRIVE and m['trashed'] is False and int(m['size'])==r['clean_size'] and m['md5Checksum']==r['clean_md5']
   p=W/f"readback-{r['index']:02}.jpg";p.write_bytes(d.raw(fid));assert sha(p)==r['clean_sha256'];v=subprocess.run([str(b.BASE/'scripts/clean-creative-metadata.sh'),'verify',str(p),'--json'],check=True,capture_output=True,text=True);assert json.loads(v.stdout)['clean'] is True;ent['destination_verified']=True;save('state.json',state)
   raw=d.meta(r['id']);assert raw['name']==r['name'] and raw['md5Checksum']==r['md5Checksum'] and raw['size']==r['size']
   if raw['parents']!=[legacy]:
    assert raw['parents']==[ROOT];intake.assert_source_writer(r['id']);d.api('PATCH','files/'+r['id'],{'addParents':legacy,'removeParents':ROOT,'supportsAllDrives':'true','fields':'id,parents'}, {})
   assert d.meta(r['id'])['parents']==[legacy];ent['legacy_verified']=True;save('state.json',state)
   inv=b.BASE/'data/ares/creative-ops/inventory/assets.jsonl'
   with Path(str(inv)+'.lock').open('a+') as il:
    fcntl.flock(il,fcntl.LOCK_EX);allrows=rows();old=[x for x in allrows if x.get('source_drive_id')==r['id']]
    if old:assert len(old)==1 and old[0]['asset_drive_id']==fid and old[0]['canonical_filename']==r['final_name']
    else:
     row={'asset_id':r['asset_id'],'original_filename':r['name'],'canonical_filename':r['final_name'],'source_manager':'Kelly','requested_by':'Kelly Nice','requested_by_discord_id':REQUESTER,'vertical':'SHEIN','country':'US','language':'EN','operation':OP,'strategy':'UNKNOWN','source_drive_id':r['id'],'asset_drive_id':fid,'original_checksum':r['raw_sha256'],'clean_checksum':r['clean_sha256'],'pixel_sha256':r['pixel_sha256'],'format':'IMG','angle':r['angle'],'claim':'FREE Baby Tees!' if r['angle']=='FREE_BABY_TEES' else 'FREE plus-size, oversized hoodies!','person':'NO_PERSON','orientation':'VERTICAL','p_orient':'NV','variant':r['variant'],'status':'01_READY','reservation_status':'RESERVADO_PELO_GESTOR','ares_eligible':False,'used_by':None,'campaign_owner':'Kelly','meta_ad_id':None,'meta_creative_id':None,'meta_image_hash':None,'meta_video_id':None,'effective_object_story_id':None,'width':1080,'height':1920,'aspect_ratio':'9:16','placement_fit':'STORY_REELS','metadata_clean':True,'first_seen_at':r['createdTime'],'last_reconciled_at':b.now_iso(),'performance_label':'UNKNOWN','thread_id':T,'webViewLink':'https://drive.google.com/file/d/'+fid+'/view','source_path':'MGS-AGENTS/CRIATIVOS/'+OP+'/IMG/99_LEGACY/'+r['name'],'asset_path':'MGS-AGENTS/CRIATIVOS/'+OP+'/IMG/01_READY/'+r['final_name'],'clean_bytes':r['clean_size'],'clean_md5':r['clean_md5'],'visual_evidence':r['visual_evidence'],'notes':'Explicit Kelly treat/move request. Source loose in UPLOAD MANUAL root; new 2026-11-01 batch only. Separate duplicate source #19 retained pending canonical duplicate archival support.'}
     with inv.open('a') as f:f.write(json.dumps(row,ensure_ascii=False)+'\n');f.flush();os.fsync(f.fileno())
   ent['inventory_verified']=True;save('state.json',state);print('verified',r['index'],r['final_name'],flush=True)
  state.update(phase='treatment_complete_archive_pending',updated_at=b.now_iso());save('state.json',state)
 print('TREATMENT',len(state['items']),'primary unique files',flush=True)
def enqueue():
 plan=load('plan.json');d=b.Drive(True);jobs=load('archive-jobs.json') or [];known={j['asset_id'] for j in jobs}
 for r in plan['items']:
  if r['disposition']=='duplicate' or r['asset_id'] in known:continue
  with b.queue_lock():
   c=b.config_load();job=b.job_for_lineage(d,c,r['asset_id']);res=b.enqueue(d,c,job);jobs.append({'asset_id':r['asset_id'],'job_id':job['jobId'],'request_id':res['requestFileId']});save('archive-jobs.json',jobs)
  print('queued',r['index'],job['jobId'],flush=True)
def audit():
 import ares_archive_storage as storage
 d=b.Drive();plan=load('plan.json');state=load('state.json');inventory=rows();index=b.read_json(b.DATA/'archive-index.json');proofs=[];duplicate_proofs=[]
 for r in plan['items']:
  if r['disposition']=='duplicate':continue
  ent=state['items'][r['id']];row=next(x for x in inventory if x.get('source_drive_id')==r['id']);assert row['asset_drive_id']==ent['dest_id'] and row['canonical_filename']==r['final_name'] and row['reservation_status']=='RESERVADO_PELO_GESTOR' and row['ares_eligible'] is False
  for fid,h,name,path in [(r['id'],r['raw_sha256'],r['name'],'stock_legacy'),(ent['dest_id'],r['clean_sha256'],r['final_name'],'stock_ready')]:
   mapping=index['mappings'][fid];storage.require_registered_mapping(mapping,index);assert mapping['stockTransferredToArchive'] is True;native=storage.meta(d,mapping['stockShortcutId']);provider=storage.meta(d,mapping['archiveId']);assert native['parents']==[plan['locations'][path]] and native['shortcutDetails']['targetId']==provider['id'] and provider['size']==str(r['clean_size'] if path=='stock_ready' else r['size']) and provider['md5Checksum']==(r['clean_md5'] if path=='stock_ready' else r['md5Checksum']);assert d.hashes(provider['id'])['sha256']==h
   if path=='stock_ready':
    cp=W/f"audit-{r['index']:02}.jpg";cp.write_bytes(d.raw(provider['id']));assert sha(cp)==h;v=subprocess.run([str(b.BASE/'scripts/clean-creative-metadata.sh'),'verify',str(cp),'--json'],check=True,capture_output=True,text=True);assert json.loads(v.stdout)['clean'] is True
  proofs.append({'source_id':r['id'],'dest_id':ent['dest_id'],'raw_sha256':r['raw_sha256'],'clean_sha256':r['clean_sha256'],'permanent_verified':True});print('audit',r['index'],'permanent pair verified',flush=True)
 pending=[r['id'] for r in selected(d)];assert set(pending)=={r['id'] for r in plan['items'] if r['disposition']=='duplicate'}
 out={'status':'partial_duplicate_control_pending','received_sources':len(plan['items']),'unique_destinations':len(proofs),'pending_scoped':len(pending),'all_metadata_clean':True,'all_reservations_preserved':True,'proofs':proofs,'pending_duplicate_ids':pending,'stock_ready':plan['locations']['stock_ready'],'stock_legacy':plan['locations']['stock_legacy'],'verified_at':b.now_iso()};save('final-audit.json',out);print(json.dumps({k:v for k,v in out.items() if k!='proofs'}),flush=True)
if __name__=='__main__':globals()[sys.argv[1]]()
