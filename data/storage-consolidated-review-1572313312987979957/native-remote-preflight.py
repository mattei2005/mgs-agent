"""Bounded native GET-only remote preflight, with separate prepare/execution/post receipts."""
import pathlib,json,os,sys,time,datetime,argparse,fcntl,importlib,importlib.util
O=pathlib.Path(__file__).parent;spec=importlib.util.spec_from_file_location('frozen_gate',O/'gate.py');assert spec and spec.loader;g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--phase',choices=['prepare','execution','post'],required=True);ap.add_argument('--limit',type=int,default=25);args=ap.parse_args();m,digest=g.load_manifest();g.verify_source_evidence(m);confirmation=None
 if args.phase=='execution':
  a=json.loads((O/'critical-approval.json').read_text());g.approval(a,digest,m);confirmation=a['confirmation_message_id']
 if args.phase=='post':g.need((O/'filesystem-result.json').exists()and all(not os.path.lexists(r['path'])for r in m['targets']),'POST_REQUIRES_REAL_TARGET_ABSENCE')
 P=pathlib.Path(m['private_root']);name='remote-'+args.phase+('-'+confirmation if confirmation else'');out=P/(name+'.jsonl');done={}
 if out.exists():
  for line in out.read_text().splitlines():
   r=json.loads(line);g.need(r['source_id']not in done and r['manifest_sha256']==digest and r['phase']==args.phase and r.get('confirmation_message_id')==confirmation,'REMOTE_RESUME_SCOPE');done[r['source_id']]=r
 g.need(set(done)<=set(m['media_expected']),'REMOTE_RESUME_IDS');todo=[sid for sid in sorted(m['media_expected'])if sid not in done][:args.limit]
 sys.path.insert(0,'/root/mgs-agent/scripts');s=importlib.import_module('ares_archive_storage');b=importlib.import_module('ares_archive_bridge');d=b.Drive(False)
 for key in ['ARES_DRIVE_AUTH_MODE','MGS_DRIVE_AUTH_PRIMARY','MGS_GOOGLE_SHEETS_AUTH_MODE','MGS_META_APP_ROLES_GOOGLE_AUTH_MODE']:g.need(os.environ[key]=='service_account','CANONICAL_SERVICE_ACCOUNT_SELECTOR')
 g.need(b.CANONICAL_SA=='mgsagent@mgs-core-prod.iam.gserviceaccount.com','CANONICAL_SA');native=d.api;cache={}
 def readonly(method,path,params=None,payload=None):
  g.need(method=='GET'and payload is None,'GET_ONLY');key=(path,json.dumps(params,sort_keys=True))
  if key not in cache:cache[key]=native(method,path,params,payload)
  return cache[key]
 d.api=readonly;setattr(s,'drive',lambda token=None,write=False:d if not write else (_ for _ in()).throw(RuntimeError('NO_WRITES')));representatives=set(sorted(m['media_expected'])[:5]+sorted(m['media_expected'])[-5:]);lock=P/(name+'.lock')
 with lock.open('a')as f:
  fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
  for sid in todo:
   e=m['media_expected'][sid];record=s.resolve_media(sid)
   if record is None:raise RuntimeError('NATIVE_RECORD_UNAVAILABLE')
   g.need(record['provider_id']==e['provider_id']and record['stock_file_id']==e['stock_file_id']and int(record['size'])==e['size']and record['md5Checksum']==e['md5']and record['sha256Checksum']==e['sha256'],'NATIVE_CURRENT_BINDING');stream=False
   if args.phase=='post'and sid in representatives:
    hashes=d.hashes(record['provider_id']);g.need(hashes['sha256']==e['sha256']and hashes['md5']==e['md5']and int(hashes['size'])==e['size'],'POST_REPRESENTATIVE_FULL_STREAM');stream=True
   proof=dict(source_id=sid,provider_id=record['provider_id'],stock_file_id=record['stock_file_id'],size=e['size'],md5=e['md5'],sha256=e['sha256'],manifest_sha256=digest,phase=args.phase,confirmation_message_id=confirmation,native_guards_passed=True,representative_full_stream=stream,observed_epoch=time.time(),SA=b.CANONICAL_SA,remote_writes=0)
   with out.open('a')as w:w.write(json.dumps(proof)+'\n');w.flush();os.fsync(w.fileno())
   done[sid]=proof
 print(json.dumps({'phase':args.phase,'new_native_IDs':len(todo),'verified_total':len(done),'expected':len(m['media_expected']),'remaining':len(m['media_expected'])-len(done),'remote_writes':0,'source_files_deleted':0}))
if __name__=='__main__':main()
