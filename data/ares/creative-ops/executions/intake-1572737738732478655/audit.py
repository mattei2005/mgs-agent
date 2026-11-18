#!/usr/bin/env python3
"""Independent exact-source permanent audit, no remote writes."""
import sys,json,pathlib,hashlib,subprocess,concurrent.futures
sys.path.insert(0,'/root/mgs-agent/scripts')
import ares_archive_bridge as b,ares_archive_storage as store,ares_archive_locations as loc,ares_autonomous_intake as intake,mgs_flat_source_compat as compat
P=pathlib.Path(__file__).parent;O=b.BASE/'data/ares/creative-ops/executions/intake-1572737738732478655';RID='3cdc595c6abd76191ad3cb7584d9110b';N=8
plan=b.read_json(O/'plan.json');req=b.read_json(b.DATA/'flat-intake-requests.json')['requests'][RID];state=b.read_json(intake.STATE);index=b.read_json(b.DATA/'archive-index.json')
rows=[json.loads(l) for l in (b.BASE/'data/ares/creative-ops/inventory/assets.jsonl').read_text().splitlines() if l.strip()]
expected={x['id'] for x in plan['items']};assert len(expected)==N and expected=={s['id'] for s in req['sources']};assert req['status']=='complete'
claims=sorted([c for c in state['claims'].values() if c['batch'].get('flat_request_id')==RID],key=lambda c:c['claimed_at']);assert all(c['status']=='complete' for c in claims)
assert {s['source_id'] for c in claims for s in c['batch']['sources']}==expected
assert set(req['completed_batches'])=={c['batch']['batch_id'] for c in claims}
D=b.Drive();ready=loc.stock_folder_for_path(D,['SHEIN_US_ES','VID','01_READY']);legacy=loc.stock_folder_for_path(D,['SHEIN_US_ES','VID','99_LEGACY'])
def audit(x):
 d=store.drive(D.token);matches=[r for r in rows if r.get('source_drive_id')==x['id'] or x['id'] in r.get('duplicate_source_drive_ids',[])];assert len(matches)==1;r=matches[0]
 assert r['operation']=='SHEIN_US_ES' and r['canonical_filename']==x['final_name'] and r['original_filename']==x['name'] and r['metadata_clean'] is True
 claim=next(c for c in claims if any(s['source_id']==x['id'] for s in c['batch']['sources']));assert intake.verify_reservation(r,claim['inventory_before'],claim['batch'])
 assert r['source_manager']=='Kelly' and r['ares_eligible'] is False and r['reservation_status']=='RESERVADO_PELO_GESTOR' and not r.get('used_by')
 entry=index['mappings'][x['id']];job=b.read_json(b.DATA/'jobs'/('job-'+entry['jobId']+'.json'));asset=next(a for a in job['assets'] if a['sourceId']==x['id'])
 native=d.meta(x['id']);assert native['id']==x['id'] and native['name']==x['name'] and not native['trashed'];assert compat.verify(d,native,asset,job) is True
 native_hash=d.hashes(x['id']);assert native_hash=={'size':x['size'],'md5':x['md5Checksum'],'sha256':x['raw_sha256']}
 records={}
 for role,logical,checksum,parent in [('raw',x['id'],x['raw_sha256'],legacy),('clean',r['asset_drive_id'],x['clean_sha256'],ready)]:
  cat=store.resolve_media(logical,token=D.token);assert cat and cat['parents']==[parent] and cat['storage_backend']=='gmail_archive'
  m=index['mappings'][logical];assert m['verified'] is True and m['stockTransferredToArchive'] is True
  assert cat['sha256Checksum']==checksum and not cat['provider_metadata']['trashed'] and not cat['stock_metadata']['trashed']
  data=d.raw(cat['provider_id']);assert hashlib.sha256(data).hexdigest()==checksum and str(len(data))==cat['size']
  if role=='clean':
   assert cat['name']==x['final_name'];f=P/f'{x["index"]:02}-audit.mp4';f.write_bytes(data)
   v=subprocess.run([str(b.BASE/'scripts/clean-creative-metadata.sh'),'verify',str(f),'--json'],capture_output=True,text=True,timeout=120);assert v.returncode==0 and json.loads(v.stdout)['clean'] is True
   p=subprocess.run(['ffprobe','-v','error','-select_streams','v:0','-show_entries','stream=width,height','-of','json',str(f)],capture_output=True,text=True,timeout=120);assert p.returncode==0;s=json.loads(p.stdout)['streams'][0];assert s['width']==x['width'] and s['height']==x['height']
  records[role]={'logical_id':logical,'provider_id':cat['provider_id'],'stock_id':cat['stock_file_id'],'parent':parent,'sha256':checksum,'permanent_verified':True}
 out={'source_id':x['id'],'asset_id':r['asset_id'],'original_filename':x['name'],'canonical_filename':x['final_name'],'format':'VID','native_original_verified':True,'raw_sha256':x['raw_sha256'],'clean_sha256':x['clean_sha256'],'reservation_preserved':True,'clean':True,'permanent_verified':True,'at':b.now_iso(),**records};b.atomic_json(O/f'audit-{x["index"]:02}.json',out);print('audited',x['index'],flush=True);return out
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:proofs=list(pool.map(audit,plan['items']))
assert len(proofs)==N and {x['source_id'] for x in proofs}==expected and all(x['permanent_verified'] for x in proofs)
ordered=[]
for c in claims:
 for s in c['batch']['sources']:
  x=next(x for x in proofs if x['source_id']==s['source_id']);ordered.append({'source_id':x['source_id'],'original':x['original_filename'],'final':x['canonical_filename']})
assert len(ordered)==N and {r['source_id'] for r in ordered}==expected
b.atomic_json(O/'rename-map.json',ordered)
audit={'status':'complete','request_id':RID,'received':N,'new':N,'duplicates':0,'pending':0,'locations':{'VID':{'stock_ready':ready,'stock_legacy':legacy}},'verified_at':b.now_iso(),'proofs':proofs}
b.atomic_json(O/'final-audit.json',audit);print(json.dumps({k:v for k,v in audit.items() if k!='proofs'},ensure_ascii=False))
