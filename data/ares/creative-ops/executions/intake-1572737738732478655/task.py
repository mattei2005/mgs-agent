#!/usr/bin/env python3
"""Task scoped adapter: frozen Kelly common request; canonical SA/intake only."""
import sys,os,json,pathlib,hashlib,subprocess,concurrent.futures,re,fcntl,time
sys.path.insert(0,'/root/mgs-agent/scripts')
import ares_archive_bridge as b
import ares_archive_locations as loc
import ares_autonomous_intake as intake
P=pathlib.Path(__file__).parent
OUT=b.BASE/'data/ares/creative-ops/executions/intake-1572737738732478655'
INV=b.BASE/'data/ares/creative-ops/inventory/assets.jsonl'
RID='3cdc595c6abd76191ad3cb7584d9110b';THREAD='1572737738732478655';OP='SHEIN_US_ES';OWNER='528c5710269d';N=8
SAN=str(b.BASE/'scripts/clean-creative-metadata.sh')
load=b.read_json;save=b.atomic_json
sha=lambda data:hashlib.sha256(data).hexdigest()
def run(args):
 p=subprocess.run(args,capture_output=True,text=True,timeout=400)
 assert p.returncode==0,p.stdout[-500:]+p.stderr[-500:]
 return p.stdout
def inventory():return [json.loads(l) for l in INV.read_text().splitlines() if l.strip()]
def probe(p):
 d=json.loads(run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(p)]));v=next(s for s in d['streams'] if s['codec_type']=='video')
 return {'width':v['width'],'height':v['height'],'duration':float(d['format']['duration']),'audio':any(s['codec_type']=='audio' for s in d['streams'])}
def frames(p):
 text=run(['ffmpeg','-v','error','-threads','1','-i',str(p),'-map','0:v:0','-f','framemd5','-'])
 return [l.split(',')[-1].strip() for l in text.splitlines() if l and not l.startswith('#')]
def audio(p):
 q=subprocess.run(['ffmpeg','-v','error','-threads','1','-i',str(p),'-map','0:a:0','-f','s16le','-'],capture_output=True,timeout=180);assert q.returncode==0
 return sha(q.stdout)
def prepare():
 req=load(OUT/'request.json');sources={s['id']:s for s in req['sources']};base=load(P/'prepared.json')
 assert req['request_id']==RID and len(base)==N and {r['source']['id'] for r in base}==set(sources)
 def one(r):
  n=r['n'];s=sources[r['source']['id']];raw=pathlib.Path(r['raw']);clean=P/f'{n:02}-clean.mp4';data=raw.read_bytes()
  assert sha(data)==s['sha256Checksum'] and hashlib.md5(data).hexdigest()==s['md5Checksum'] and str(len(data))==s['size']
  if not clean.exists():run([SAN,'clean',str(raw),'--out',str(clean),'--agent','ares'])
  assert json.loads(run([SAN,'verify',str(clean),'--json']))['clean'] is True
  t=probe(raw);assert t==probe(clean);fh=frames(raw);assert fh and fh==frames(clean)
  ah=audio(raw) if t['audio'] else None;assert ah==(audio(clean) if t['audio'] else None)
  shots=[]
  for j,frac in enumerate([.01,.2,.5,.8,.98]):
   f=P/f'{n:02}-clean-{j}.jpg';run(['ffmpeg','-v','error','-threads','1','-ss',str(t['duration']*frac),'-i',str(clean),'-frames:v','1','-vf','scale=240:-1','-y',str(f)]);shots.append(str(f))
  out={**s,**t,'index':n,'raw_path':str(raw),'clean_path':str(clean),'raw_sha256':sha(data),'clean_sha256':sha(clean.read_bytes()),'clean_size':clean.stat().st_size,'clean_md5':hashlib.md5(clean.read_bytes()).hexdigest(),'metadata_clean':True,'frame_count':len(fh),'frames_equal':True,'audio_equal':True,'audio_sha256':ah,'frames':shots}
  save(OUT/f'prepared-{n:02}.json',out);print('prepared',n,flush=True);return out
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:items=list(ex.map(one,base))
 save(OUT/'clean-prepared.json',{'request_id':RID,'items':items})
 from PIL import Image,ImageDraw
 for start in range(0,N,4):
  chunk=items[start:start+4];im=Image.new('RGB',(1200,len(chunk)*455),'white');dr=ImageDraw.Draw(im)
  for y,x in enumerate(chunk):
   dr.text((4,y*455),f'CLEAN {x["index"]:02} / opening,20,50,80,ending',fill='black')
   for j,f in enumerate(x['frames']):
    a=Image.open(f);a.thumbnail((240,425));im.paste(a,(240*j,y*455+25))
  im.save(P/f'clean-review-{start+1:02}-{start+len(chunk):02}.jpg')
 print('PREPARED_VERIFIED',len(items),flush=True)
def folder(d,parent,name,create=False):
 rows=[r for r in d.listing(parent) if r['name']==name];assert len(rows)<=1,'AMBIGUOUS_FOLDER'
 if rows:
  m=d.meta(rows[0]['id']);assert m['mimeType']==b.FOLDER and not m['trashed'];return m['id']
 if not create:return None
 assert d.meta(parent).get('driveId')==b.SOURCE_DRIVE,'NO_MYDRIVE_WRITE'
 fid=d.api('POST','files',{'supportsAllDrives':'true','fields':'id'},{'name':name,'mimeType':b.FOLDER,'parents':[parent]})['id'];m=d.meta(fid);assert m['parents']==[parent] and m['driveId']==b.SOURCE_DRIVE
 return fid
def plan():
 data=load(OUT/'clean-prepared.json');reviews=load(OUT/'reviews.json');req=load(b.DATA/'flat-intake-requests.json')['requests'][RID]
 assert data['request_id']==req['request_id']==RID and req['destination_mode']=='common'
 assert {x['id'] for x in data['items']}=={s['id'] for s in req['sources']}==set(reviews) and len(reviews)==N
 d=b.Drive();rows=inventory();names={r['canonical_filename'] for r in rows if r.get('canonical_filename')}
 ready=loc.stock_folder_for_path(d,[OP,'VID','01_READY']);names.update(x['name'] for x in d.listing(ready))
 hashes={}
 for row in rows:
  for k in ['original_checksum','clean_checksum']:
   if row.get(k):hashes.setdefault(row[k],set()).add(row['asset_id'])
 seen=set()
 for x in data['items']:
  v=reviews[x['id']];assert v['qa'] is True and v['language']=='ES' and v['person'] in ['PV','NV']
  assert x['raw_sha256'] not in hashes and x['clean_sha256'] not in hashes,'DUPLICATE_REQUIRES_BRANCH'
  assert x['clean_sha256'] not in seen,'BATCH_DUPLICATE';seen.add(x['clean_sha256']);x.update(v)
  group=f'{OP}_VID_{x["angle"]}_{x["person"]}';used=[int(m[1]) for n in names if (m:=re.fullmatch(re.escape(group)+r'_(\d{3})\.mp4',n))];num=max(used,default=0)+1;assert num<=999
  x.update(final_name=f'{group}_{num:03}.mp4',variant=f'{num:03}',asset_id='asset_'+sha((THREAD+':'+x['id']).encode())[:20]);names.add(x['final_name'])
 assert len({x['final_name'] for x in data['items']})==N
 data.update(operation=OP,thread_id=THREAD,destination_mode='common',expected_count=N,dry_run_remote_writes=0,created_at=b.now_iso(),stock_ready=ready)
 assert not (OUT/'plan.json').exists(),'IMMUTABLE_PLAN_EXISTS';save(OUT/'plan.json',data)
 print('PLAN_VALID',N,[(x['index'],x['final_name']) for x in data['items']],flush=True)
def no_other_writer():
 me=os.getpid()
 for p in pathlib.Path('/proc').iterdir():
  if not p.name.isdigit() or int(p.name)==me:continue
  try:args=(p/'cmdline').read_bytes().decode().split('\0')
  except (OSError,UnicodeError):continue
  for arg in args[1:]:
   if arg.endswith('ares_autonomous_intake.py') and any(v in args for v in ['complete','claim']):raise RuntimeError('CANONICAL_WRITER_ACTIVE')
 lock=b.DATA/'.intake-state.lock'
 if lock.exists():
  st=lock.stat();dev=f'{os.major(st.st_dev):02x}:{os.minor(st.st_dev):02x}:{st.st_ino}'
  assert not any(dev in l for l in pathlib.Path('/proc/locks').read_text().splitlines()),'CANONICAL_LOCK_BUSY'
def execute(bid):
 no_other_writer();plan=load(OUT/'plan.json');batch=load(b.DATA/'intake-batches'/f'batch-{bid}.json')
 assert batch['flat_request_id']==RID and batch['operation']==OP and batch['destination_mode']=='common'
 os.environ['ARES_INTAKE_BATCH_ID']=bid
 selected={x['id']:x for x in plan['items']};items=[selected[s['source_id']] for s in batch['sources']]
 for s,x in zip(batch['sources'],items):
  assert sha(pathlib.Path(x['raw_path']).read_bytes())==s['sha256']==x['raw_sha256'];assert sha(pathlib.Path(x['clean_path']).read_bytes())==x['clean_sha256']
 frozen={**{k:v for k,v in plan.items() if k!='items'},'batch_id':bid,'items':items};target=b.DATA/'intake-batches'/f'batch-{bid}.plan.json'
 if target.exists():assert load(target)==frozen
 else:save(target,frozen)
 with (b.DATA/f'intake-operation-{OP}.lock').open('a+') as op,(OUT/'writer.lock').open('a+') as lock:
  fcntl.flock(op,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  save(OUT/f'phase-{bid}.json',{'phase':'execute','batch_id':bid,'pid':os.getpid(),'at':b.now_iso()})
  out=run([sys.executable,str(b.BASE/'scripts/ares_autonomous_intake.py'),'claim','--batch-id',bid,'--owner',OWNER]);(OUT/f'claim-{bid}.log').write_text(out)
  d=b.Drive(True);root=d.meta(b.SOURCE_ROOT);assert root['driveId']==b.SOURCE_DRIVE and root['capabilities']['canAddChildren'];assert d.api('GET','drives/'+b.SOURCE_DRIVE,{'fields':'id,name'})['name']=='MGS-AGENTS'
  opid=folder(d,b.SOURCE_ROOT,OP,True);vid=folder(d,opid,'VID',True);ready=folder(d,vid,'01_READY',True);legacy=folder(d,vid,'99_LEGACY',True)
  for x in items:
   proofpath=OUT/f'treated-{x["index"]:02}.json';proof=load(proofpath,{})
   existing=[r for r in inventory() if r.get('source_drive_id')==x['id']]
   if existing:
    assert len(existing)==1 and existing[0]['clean_checksum']==x['clean_sha256'];print('already_treated',x['index'],flush=True);continue
   m=d.api('GET','files/'+x['id'],{'supportsAllDrives':'true','fields':'id,name,parents,driveId,size,md5Checksum,version,trashed,capabilities(canDownload,canEdit,canMoveItemWithinDrive)'})
   assert m['name']==x['name'] and not m['trashed'] and m['driveId']==b.SOURCE_DRIVE and m['md5Checksum']==x['md5Checksum'] and m['size']==x['size'] and m['parents'] in [x['parents'],[legacy]]
   assert all(m['capabilities'].get(k) for k in ['canEdit','canDownload','canMoveItemWithinDrive'])
   cid=proof.get('clean_id')
   if not cid:
    dat=pathlib.Path(x['clean_path']).read_bytes();assert sha(dat)==x['clean_sha256'];cid=d.upload_once(ready,x['final_name'],dat,'video/mp4','intake-'+RID+'-'+x['id'],'creative-clean');proof.update(source_id=x['id'],clean_id=cid,uploaded_at=b.now_iso());save(proofpath,proof)
   cm=d.meta(cid);assert cm['name']==x['final_name'] and cm['parents']==[ready] and cm['driveId']==b.SOURCE_DRIVE and not cm['trashed'] and cm['md5Checksum']==x['clean_md5']
   dat=d.raw(cid);assert sha(dat)==x['clean_sha256'] and len(dat)==x['clean_size'];rb=P/f'{x["index"]:02}-readback.mp4';rb.write_bytes(dat);assert json.loads(run([SAN,'verify',str(rb),'--json']))['clean'] is True
   proof.update(clean_verified=True,clean_sha256=x['clean_sha256']);save(proofpath,proof)
   if m['parents']!=[legacy]:
    assert m['parents']==x['parents'];d.api('PATCH','files/'+x['id'],{'supportsAllDrives':'true','addParents':legacy,'removeParents':m['parents'][0],'fields':'id,parents'}, {})
   rm=d.meta(x['id']);assert rm['parents']==[legacy] and rm['name']==x['name'] and rm['md5Checksum']==x['md5Checksum'] and not rm['trashed']
   row={'asset_id':x['asset_id'],'source_drive_id':x['id'],'asset_drive_id':cid,'original_filename':x['name'],'source_filename':x['name'],'canonical_filename':x['final_name'],'operation':OP,'vertical':'SHEIN','country':'US','language':'ES','format':'VID','angle':x['angle'],'p_orient':x['person'],'variant':x['variant'],'width':x['width'],'height':x['height'],'duration_seconds':x['duration'],'original_checksum':x['raw_sha256'],'clean_checksum':x['clean_sha256'],'metadata_clean':True,'first_seen_at':b.now_iso(),'created_at':b.now_iso(),'source_manager':'Kelly','source_manager_code':'g005','reservation_status':'RESERVADO_PELO_GESTOR','ares_eligible':False,'used_by':[],'campaign_owner':None,'status':'01_READY','asset_path':f'MGS-AGENTS/CRIATIVOS/{OP}/VID/01_READY/{x["final_name"]}','source_path':f'MGS-AGENTS/CRIATIVOS/{OP}/VID/99_LEGACY/{x["name"]}','thread_id':THREAD,'request_message_id':batch['request_message_id'],'request_channel_id':batch['request_channel_id'],'requested_by_discord_id':batch['requested_by_discord_id'],'requested_by':'pedido humano de '+batch['requested_by_discord_id'],'notes':'Kelly explicit common US SHEIN ES; source EN filename label preserved; Spanish media reviewed. No campaign/eligibility release.','visible_claim':x['claim'],'visual_qa':{'passed':True,'frames_equal':True,'audio_equal':True,'frame_count':x['frame_count']},'webViewLink':'https://drive.google.com/file/d/'+cid+'/view'}
   with INV.with_suffix('.jsonl.lock').open('a+') as il:
    fcntl.flock(il,fcntl.LOCK_EX);assert not any(r.get('source_drive_id')==x['id'] for r in inventory())
    with INV.open('a') as f:f.write(json.dumps(row,ensure_ascii=False,separators=(',',':'))+'\n');f.flush();os.fsync(f.fileno())
   assert len([r for r in inventory() if r.get('source_drive_id')==x['id']])==1
   proof.update(raw_parent_verified=True,inventory_verified=True,treated_at=b.now_iso());save(proofpath,proof);print('treated',x['index'],x['final_name'],flush=True)
  pairs=[]
  for x in items:
   r=next(r for r in inventory() if r.get('source_drive_id')==x['id']);pairs.extend([x['id'],r['asset_drive_id']])
  polls=[];prev=None;stable=0;deadline=time.monotonic()+240
  while time.monotonic()<deadline:
   snap=[]
   for fid in pairs:
    m=d.meta(fid);snap.append({k:m.get(k) for k in ['id','parents','version','size','md5Checksum']})
   stable=stable+1 if snap==prev else 1;prev=snap;polls.append({'at':b.now_iso(),'metadata':snap,'consecutive':stable});save(OUT/f'stability-{bid}.json',polls)
   if stable>=3:break
   time.sleep(12)
  assert stable>=3,'NATIVE_PAIR_STABILITY';print('BATCH_TREATMENT_VERIFIED',bid,flush=True)
if __name__=='__main__':
 if sys.argv[1]=='prepare':prepare()
 elif sys.argv[1]=='plan':plan()
 elif sys.argv[1]=='execute':execute(sys.argv[2])
