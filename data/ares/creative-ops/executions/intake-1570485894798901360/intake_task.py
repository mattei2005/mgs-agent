#!/usr/bin/env python3
"""Task-scoped adapter. Canonical SA, single frozen request, no campaign/delete."""
import sys,os,json,pathlib,hashlib,subprocess,concurrent.futures,re,fcntl,time,unicodedata
sys.path.insert(0,'/root/mgs-agent/scripts')
import ares_archive_bridge as b
import ares_archive_locations as loc
P=pathlib.Path(__file__).parent
OUT=b.BASE/'data/ares/creative-ops/executions/intake-1570485894798901360'
OUT.mkdir(parents=True,exist_ok=True)
INV=b.BASE/'data/ares/creative-ops/inventory/assets.jsonl'
RID='3b3c569a38ec154a9cee915fb56c2701'; THREAD='1570485894798901360'; OP='SHEIN_US_ES'; OWNER='528c5710269d'
SAN=str(b.BASE/'scripts/clean-creative-metadata.sh')
def save(path,x): b.atomic_json(path,x)
def load(path,default=None): return b.read_json(path,default)
def run(args):
 x=subprocess.run(args,capture_output=True,text=True,timeout=400)
 if x.returncode:raise RuntimeError(str(args[0])+': '+x.stderr[-500:]+x.stdout[-500:])
 return x.stdout
def sha(data):return hashlib.sha256(data).hexdigest()
def probe(path):
 x=json.loads(run(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(path)]));s=next(s for s in x['streams'] if s['codec_type']=='video')
 return {'width':s['width'],'height':s['height'],'duration':float(x['format']['duration']),'audio':any(s['codec_type']=='audio' for s in x['streams'])}
def framehash(path):
 s=run(['ffmpeg','-v','error','-threads','1','-i',str(path),'-map','0:v:0','-f','framemd5','-']);return [l.split(',')[-1].strip() for l in s.splitlines() if l and not l.startswith('#')]
def audiohash(path):
 x=subprocess.run(['ffmpeg','-v','error','-threads','1','-i',str(path),'-map','0:a:0','-f','s16le','-'],capture_output=True,timeout=120)
 if x.returncode:raise RuntimeError('AUDIO_DECODE')
 return sha(x.stdout)
def prepare_one(pair):
 i,s=pair;fid=s['id'];existing=load(OUT/f'prepared-{i:02}.json')
 if existing and pathlib.Path(existing['clean_path']).exists():return existing
 d=b.Drive();raw=P/(fid+'-raw.mp4');clean=P/(fid+'-clean.mp4')
 if not raw.exists():raw.write_bytes(d.raw(fid))
 data=raw.read_bytes();assert str(len(data))==s['size'] and hashlib.md5(data).hexdigest()==s['md5Checksum']
 tech=probe(raw)
 if not clean.exists():run([SAN,'clean',str(raw),'--out',str(clean),'--agent','ares'])
 assert json.loads(run([SAN,'verify',str(clean),'--json']))['clean'] is True
 ct=probe(clean);assert tech==ct
 rh,ch=framehash(raw),framehash(clean);assert rh==ch and rh
 ah=audiohash(raw) if tech['audio'] else None;ac=audiohash(clean) if tech['audio'] else None;assert ah==ac
 frames=[]
 for j,t in enumerate([.05,tech['duration']*.2,tech['duration']*.5,tech['duration']*.8,max(0,tech['duration']-.1)]):
  f=P/f'{i:02}-clean-{j}.jpg';run(['ffmpeg','-v','error','-threads','1','-ss',str(t),'-i',str(clean),'-frames:v','1','-vf','scale=240:-1','-y',str(f)]);frames.append(str(f))
 out={**s,**tech,'index':i,'raw_path':str(raw),'clean_path':str(clean),'raw_sha256':sha(data),'clean_sha256':sha(clean.read_bytes()),'clean_size':clean.stat().st_size,'clean_md5':hashlib.md5(clean.read_bytes()).hexdigest(),'metadata_clean':True,'frame_count':len(rh),'frames_equal':True,'audio_equal':True,'audio_sha256':ah,'frames':frames}
 save(OUT/f'prepared-{i:02}.json',out);print('prepared',i,flush=True);return out

def prepare():
 sources=sorted(load(P/'recent-sources.json'),key=lambda s:(s['createdTime'],s['id']))
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:items=list(pool.map(prepare_one,enumerate(sources,1)))
 assert len(items)==40 and len({x['id'] for x in items})==40
 save(OUT/'prepared.json',{'request_id':RID,'items':items})
 from PIL import Image,ImageDraw
 for start in range(0,len(items),5):
  chunk=items[start:start+5];im=Image.new('RGB',(1200,len(chunk)*455),'white');dr=ImageDraw.Draw(im)
  for y,x in enumerate(chunk):
   dr.text((4,y*455),f"CLEAN {x['index']:02} / five timeline frames",fill='black')
   for j,f in enumerate(x['frames']):
    a=Image.open(f);a.thumbnail((240,425));im.paste(a,(240*j,y*455+25))
  im.save(P/f'review-{start+1:02}-{start+len(chunk):02}.jpg')
 print('PREPARATION_COMPLETE',len(items),flush=True)

def inventory():return [json.loads(l) for l in INV.read_text().splitlines() if l.strip()]
def folder(d,parent,name,create=False):
 rows=[x for x in d.listing(parent) if x['name']==name]
 assert len(rows)<=1,'AMBIGUOUS_FOLDER'
 if rows:
  m=d.meta(rows[0]['id']);assert m['mimeType']==b.FOLDER and not m['trashed'];return m['id']
 if not create:return None
 assert d.meta(parent).get('driveId')==b.SOURCE_DRIVE,'NO_MYDRIVE_WRITE'
 fid=d.api('POST','files',{'supportsAllDrives':'true','fields':'id'},{'name':name,'mimeType':b.FOLDER,'parents':[parent]})['id'];m=d.meta(fid);assert m['parents']==[parent] and m['driveId']==b.SOURCE_DRIVE
 return fid

def plan():
 data=load(OUT/'prepared.json');reviews=load(OUT/'reviews.json');assert set(reviews)=={x['id'] for x in data['items']}
 d=b.Drive();rows=inventory();names={r.get('canonical_filename') for r in rows if r.get('canonical_filename')}
 for r in load(b.DATA/'flat-intake-requests.json')['requests'].values():
  if r['request_id']==RID:assert r['destination_mode']=='common'
 # Live stock filenames supplement inventory; absence is read-only, never creates.
 ready=loc.stock_folder_for_path(d,[OP,'VID','01_READY']);names.update(x['name'] for x in d.listing(ready))
 hashes={r.get(k):r for r in rows for k in ['original_checksum','clean_checksum'] if r.get(k)}
 clean_seen={}
 for x in data['items']:
  v=reviews[x['id']];assert v['qa'] is True and v['person'] in ['PV','NV'] and v['language']=='ES'
  assert x['raw_sha256'] not in hashes and x['clean_sha256'] not in hashes,'EXISTING_DUPLICATE_REQUIRES_BRANCH'
  assert x['clean_sha256'] not in clean_seen,'WITHIN_BATCH_DUPLICATE_REQUIRES_BRANCH'
  clean_seen[x['clean_sha256']]=x['id'];x.update(v)
  group=f"{OP}_VID_{x['angle']}_{x['person']}";used=[int(m[1]) for n in names if (m:=re.fullmatch(re.escape(group)+r'_(\d{3})\.mp4',n))]
  variant=max(used,default=0)+1;assert variant<=999
  x['final_name']=f'{group}_{variant:03}.mp4';x['variant']=f'{variant:03}';names.add(x['final_name'])
  x['asset_id']='asset_'+sha((THREAD+':'+x['id']).encode())[:20]
 assert len({x['final_name'] for x in data['items']})==40
 data.update(operation=OP,thread_id=THREAD,destination_mode='common',expected_count=40,dry_run_remote_writes=0,created_at=b.now_iso(),stock_ready=ready)
 assert not (OUT/'plan.json').exists(),'FROZEN_PLAN_EXISTS'
 save(OUT/'plan.json',data);print('PLAN_VALID',len(data['items']),flush=True)

def assert_no_other_executor():
 me=os.getpid()
 for p in pathlib.Path('/proc').iterdir():
  if not p.name.isdigit() or int(p.name)==me:continue
  try:args=(p/'cmdline').read_bytes().decode().split('\0')
  except (OSError,UnicodeError):continue
  for a in args[1:]:
   if a.endswith('ares_autonomous_intake.py') and any(v in args for v in ['complete','claim']):raise RuntimeError('CANONICAL_WRITER_ACTIVE')
 lock=b.DATA/'.intake-state.lock';st=lock.stat() if lock.exists() else None
 if st:
  dev=f'{os.major(st.st_dev):02x}:{os.minor(st.st_dev):02x}:{st.st_ino}'
  for line in pathlib.Path('/proc/locks').read_text().splitlines():
   if dev in line:raise RuntimeError('CANONICAL_LOCK_BUSY')

def execute(batchid):
 assert_no_other_executor();plan=load(OUT/'plan.json');batch=load(b.DATA/'intake-batches'/f'batch-{batchid}.json');assert batch['flat_request_id']==RID
 os.environ['ARES_INTAKE_BATCH_ID']=batchid
 cp=subprocess.run([sys.executable,str(b.BASE/'scripts/ares_autonomous_intake.py'),'claim','--batch-id',batchid,'--owner',OWNER],capture_output=True,text=True);(OUT/f'claim-{batchid}.log').write_text(cp.stdout+cp.stderr);assert cp.returncode==0,cp.stdout[-500:]
 d=b.Drive(True);root=d.meta(b.SOURCE_ROOT);assert root['driveId']==b.SOURCE_DRIVE and root['capabilities']['canAddChildren']
 assert d.api('GET','drives/'+b.SOURCE_DRIVE,{'fields':'id,name'})['name']=='MGS-AGENTS'
 op=folder(d,b.SOURCE_ROOT,OP,True);vid=folder(d,op,'VID',True);ready=folder(d,vid,'01_READY',True);legacy=folder(d,vid,'99_LEGACY',True)
 ids={s['source_id'] for s in batch['sources']}
 for x in plan['items']:
  if x['id'] not in ids:continue
  proofpath=OUT/f"treated-{x['index']:02}.json";proof=load(proofpath,{})
  existing=[r for r in inventory() if r.get('source_drive_id')==x['id']]
  if existing:
   assert len(existing)==1 and existing[0]['clean_checksum']==x['clean_sha256'];print('already_treated',x['index'],flush=True);continue
  m=d.api('GET','files/'+x['id'],{'supportsAllDrives':'true','fields':'id,name,parents,driveId,size,md5Checksum,trashed,capabilities(canDownload,canEdit,canMoveItemWithinDrive)'})
  assert m['name']==x['name'] and not m['trashed'] and m['driveId']==b.SOURCE_DRIVE and m['md5Checksum']==x['md5Checksum'] and m['size']==x['size']
  assert m['parents'] in [[x['parents'][0]],[legacy]]
  assert m['capabilities'].get('canEdit') and m['capabilities'].get('canDownload') and m['capabilities'].get('canMoveItemWithinDrive')
  cleanid=proof.get('clean_id')
  if not cleanid:
   data=pathlib.Path(x['clean_path']).read_bytes();assert sha(data)==x['clean_sha256']
   cleanid=d.upload_once(ready,x['final_name'],data,'video/mp4','intake-'+RID+'-'+x['id'],'creative-clean')
   proof.update(source_id=x['id'],clean_id=cleanid,uploaded_at=b.now_iso());save(proofpath,proof)
  cm=d.meta(cleanid);assert cm['name']==x['final_name'] and cm['parents']==[ready] and cm['driveId']==b.SOURCE_DRIVE and not cm['trashed'] and cm['md5Checksum']==x['clean_md5']
  binary=d.raw(cleanid);assert sha(binary)==x['clean_sha256'] and len(binary)==x['clean_size'];rb=P/(x['id']+'-readback.mp4');rb.write_bytes(binary);assert json.loads(run([SAN,'verify',str(rb),'--json']))['clean'] is True
  proof.update(clean_verified=True,clean_sha256=x['clean_sha256']);save(proofpath,proof)
  if m['parents']!=[legacy]:
   assert m['parents']==[x['parents'][0]]
   d.api('PATCH','files/'+x['id'],{'supportsAllDrives':'true','addParents':legacy,'removeParents':m['parents'][0],'fields':'id,parents'}, {})
  rm=d.meta(x['id']);assert rm['parents']==[legacy] and rm['name']==x['name'] and rm['md5Checksum']==x['md5Checksum'] and not rm['trashed']
  row={'asset_id':x['asset_id'],'source_drive_id':x['id'],'asset_drive_id':cleanid,'original_filename':x['name'],'source_filename':x['name'],'canonical_filename':x['final_name'],'operation':OP,'vertical':'SHEIN','country':'US','language':'ES','format':'VID','angle':x['angle'],'p_orient':x['person'],'variant':x['variant'],'width':x['width'],'height':x['height'],'duration_seconds':x['duration'],'original_checksum':x['raw_sha256'],'clean_checksum':x['clean_sha256'],'metadata_clean':True,'first_seen_at':b.now_iso(),'created_at':b.now_iso(),'source_manager':'Kelly','source_manager_code':'g005','reservation_status':'RESERVADO_PELO_GESTOR','ares_eligible':False,'used_by':[],'campaign_owner':None,'status':'01_READY','asset_path':f"MGS-AGENTS/CRIATIVOS/{OP}/VID/01_READY/{x['final_name']}",'source_path':f"MGS-AGENTS/CRIATIVOS/{OP}/VID/99_LEGACY/{x['name']}",'thread_id':THREAD,'request_message_id':batch['request_message_id'],'request_channel_id':batch['request_channel_id'],'requested_by_discord_id':batch['requested_by_discord_id'],'requested_by':'pedido humano de '+batch['requested_by_discord_id'],'notes':'Explicit Kelly common request; source EN/INGLES label preserved; actual Spanish headline reviewed; no campaign or eligibility release.','visible_claim':x['claim'],'visual_qa':{'passed':True,'frames_equal':True,'audio_equal':True,'frame_count':x['frame_count']},'webViewLink':'https://drive.google.com/file/d/'+cleanid+'/view'}
  with INV.with_suffix('.jsonl.lock').open('a+') as lock:
   fcntl.flock(lock,fcntl.LOCK_EX);assert not any(r.get('source_drive_id')==x['id'] for r in inventory())
   with INV.open('a') as f:f.write(json.dumps(row,ensure_ascii=False,separators=(',',':'))+'\n');f.flush();os.fsync(f.fileno())
  assert len([r for r in inventory() if r.get('source_drive_id')==x['id']])==1
  proof.update(raw_parent_verified=True,inventory_verified=True,treated_at=b.now_iso());save(proofpath,proof);print('treated',x['index'],x['final_name'],flush=True)
 pairs=[]
 for x in plan['items']:
  if x['id'] in ids:
   r=next(r for r in inventory() if r.get('source_drive_id')==x['id']);pairs.extend([x['id'],r['asset_drive_id']])
 polls=[];prev=None;stable=0
 for i in range(6):
  snap=[{k:d.meta(fid).get(k) for k in []} for fid in []] # one exact metadata read per ID below
  snap=[]
  for fid in pairs:
   mm=d.meta(fid);snap.append({k:mm.get(k) for k in ['id','parents','version','size','md5Checksum']})
  stable=stable+1 if snap==prev else 1;prev=snap;polls.append({'at':b.now_iso(),'metadata':snap})
  if stable>=3:break
  time.sleep(12)
 assert stable>=3,'NATIVE_PAIR_STABILITY';save(OUT/f'stability-{batchid}.json',polls)
 print('BATCH_TREATMENT_VERIFIED',batchid,flush=True)

if __name__=='__main__':
 action=sys.argv[1]
 if action=='prepare':prepare()
 elif action=='plan':plan()
 elif action=='execute':
  batchid=sys.argv[2];batch=load(b.DATA/'intake-batches'/f'batch-{batchid}.json');plan=load(OUT/'plan.json')
  assert batch['flat_request_id']==RID and batch['operation']==OP and batch['manager_name']=='Kelly' and batch['destination_mode']=='common'
  selected={x['id']:x for x in plan['items']}
  for s in batch['sources']:
   x=selected[s['source_id']];assert sha(pathlib.Path(x['raw_path']).read_bytes())==s['sha256']==x['raw_sha256'];assert sha(pathlib.Path(x['clean_path']).read_bytes())==x['clean_sha256']
   assert json.loads(run([SAN,'verify',x['clean_path'],'--json']))['clean'] is True
  frozen={**{k:v for k,v in plan.items() if k!='items'},'batch_id':batchid,'items':[selected[s['source_id']] for s in batch['sources']]}
  target=b.DATA/'intake-batches'/f'batch-{batchid}.plan.json'
  if target.exists():assert load(target)==frozen
  else:save(target,frozen)
  with (b.DATA/f'intake-operation-{OP}.lock').open('a+') as op,(OUT/'writer.lock').open('a+') as lock:
   fcntl.flock(op,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
   save(OUT/f'phase-{batchid}.json',{'batch_id':batchid,'phase':'execute','pid':os.getpid(),'at':b.now_iso()});execute(batchid)
