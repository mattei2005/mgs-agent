"""Native archive resolver and full-stream GET verification, bounded and append-only."""
import sys,pathlib,json,datetime,os,time,argparse
sys.path.insert(0,'/root/mgs-agent/scripts');import importlib
s=importlib.import_module('ares_archive_storage');b=importlib.import_module('ares_archive_bridge')
O=pathlib.Path(__file__).parent;rows=json.loads((O/'all-media-archive-join.json').read_text())['matches'];expected={}
for row in rows:
 for e in row['mapping_candidates']:
  value=dict(source_id=e['source_id'],provider_id=e['archive_id'],size=row['metadata']['size'],sha256=row['sha256'])
  if e['source_id']in expected:assert expected[e['source_id']]==value
  expected[e['source_id']]=value
out=O/'all-media-native-remote-readback.jsonl';done={}
if out.exists():
 for line in out.read_text().splitlines():
  proof=json.loads(line);assert proof['source_id']not in done;done[proof['source_id']]=proof
assert set(done)<=set(expected);ap=argparse.ArgumentParser();ap.add_argument('--limit',type=int,default=10);args=ap.parse_args();d=b.Drive(False)
for key in ['ARES_DRIVE_AUTH_MODE','MGS_DRIVE_AUTH_PRIMARY','MGS_GOOGLE_SHEETS_AUTH_MODE','MGS_META_APP_ROLES_GOOGLE_AUTH_MODE']:assert os.environ[key]=='service_account'
assert b.CANONICAL_SA=='mgsagent@mgs-core-prod.iam.gserviceaccount.com';native=d.api;cache={}
def readonly(method,path,params=None,payload=None):
 assert method=='GET'and payload is None,'ONLY_GET';key=(path,json.dumps(params,sort_keys=True))
 if key not in cache:cache[key]=native(method,path,params,payload)
 return cache[key]
d.api=readonly
setattr(s,'drive',lambda token=None,write=False:d if not write else (_ for _ in()).throw(RuntimeError('NO_WRITES')))
batch=[k for k in sorted(expected)if k not in done][:args.limit]
for sid in batch:
 row=expected[sid];record=s.resolve_media(sid);assert record and record['provider_id']==row['provider_id'],'PROVIDER_BINDING';hashes=d.hashes(record['provider_id']);assert hashes['sha256']==row['sha256']and int(hashes['size'])==row['size'],'NATIVE_STREAM_HASH_SIZE';proof=dict(status='PASS',source_id=sid,provider_id=record['provider_id'],stock_file_id=record['stock_file_id'],hashes=hashes,native_resolver_guards_kept=True,SA=b.CANONICAL_SA,remote_writes=0,at=datetime.datetime.now().astimezone().isoformat())
 with out.open('a')as f:f.write(json.dumps(proof)+'\n');f.flush();os.fsync(f.fileno())
 done[sid]=proof
print(json.dumps({'new_native_verified_IDs':len(batch),'verified_total':len(done),'expected':len(expected),'remaining':len(expected)-len(done),'remote_writes':0,'source_files_deleted':0}))
