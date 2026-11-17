"""Retained-only remote dump file recovery into anonymous RAM; never start a DB or write a payload to disk."""
import argparse,ast,copy,datetime,gzip,importlib.util,json,os,pathlib,re,shlex,stat,subprocess,time
from typing import Any
R=pathlib.Path('/root/mgs-agent');A=R/'apps/finance-system';O=pathlib.Path(__file__).parent;P=pathlib.Path('/root/.hermes/secure-backups/storage-rollback-dumps-1572270579850153987')
def sha(p):return subprocess.check_output(['sha256sum',str(p)],text=True).split()[0]
def need(v,msg):
 if not v:raise RuntimeError(msg)
def bootstrap():
 prior=json.loads((R/'data/storage-finance-archives-1572257170626580601/manifest.json').read_text());hashes=prior['transport_source_hashes']
 for p,h in hashes.items():need(sha(p)==h,'CANONICAL_TRANSPORT_SOURCE_DRIFT')
 auth=R/'scripts/mgs_google_workspace_auth.py';f=next(x for x in ast.parse(auth.read_text()).body if isinstance(x,ast.FunctionDef)and x.name=='load_env');e={'BASE':R,'Path':pathlib.Path,'os':os};exec(compile(ast.fix_missing_locations(ast.Module(body=[f],type_ignores=[])),str(auth),'exec'),e);e['load_env']();need(bool(os.environ.get('OP_SERVICE_ACCOUNT_TOKEN')),'CANONICAL_ENV_REQUIRED')
 helper=A/'deploy/runcloud_ops.py';nodes:list[ast.stmt]=[n for n in ast.parse(helper.read_text()).body if isinstance(n,(ast.Import,ast.ImportFrom))or isinstance(n,ast.FunctionDef)and n.name in {'op','secret'}or isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='VAULT'for t in n.targets)];h:dict[str,Any]={};exec(compile(ast.fix_missing_locations(ast.Module(body=nodes,type_ignores=[])),str(helper),'exec'),h)
 source=A/'finance_gam_revenue_sync.py';node=copy.deepcopy(next(x for x in ast.parse(source.read_text()).body if isinstance(x,ast.FunctionDef)and x.name=='ssh'))
 # Preserve native SSH flags, credential pipe and timeout; adapt only decoding and secret-safe errors.
 changed=0
 for item in ast.walk(node):
  if isinstance(item,ast.If)and isinstance(item.test,ast.Attribute)and item.test.attr=='returncode':item.body=ast.parse("raise RuntimeError('READONLY_BINARY_SSH_TRANSPORT_FAILED')").body;changed+=1
 last=node.body[-1]
 if not isinstance(last,ast.Return):raise RuntimeError('SSH_RETURN_SHAPE')
 last.value=ast.parse('result.stdout',mode='eval').body;changed+=1;need(changed==2,'EXACT_BINARY_ADAPTER_DELTA');node.returns=None
 ns:dict[str,Any]={'os':os,'subprocess':subprocess,'runcloud_secret':h['secret'],'_RUN_CLOUD_PASSWORD':None};exec(compile(ast.fix_missing_locations(ast.Module(body=[node],type_ignores=[])),str(source)+'::readonly_binary','exec'),ns)
 return ns['ssh'],hashes

def recover(row,transport):
 remote=row['remote_candidates'][0];need(remote.startswith('/home/zeus/mgs-finance-backups/')and'..'not in pathlib.PurePosixPath(remote).parts and bool(re.fullmatch(r'[A-Za-z0-9_./-]+',remote)),'REMOTE_EXACT_ALLOWLIST')
 mem=int(next(x.split()[1]for x in pathlib.Path('/proc/meminfo').read_text().splitlines()if x.startswith('MemAvailable:')))*1024;size=row['metadata']['size'];need(mem>4*size+2*1024**3,'MEMORY_HEADROOM')
 q=shlex.quote(remote);meta_command='sha256sum -- '+q+' && stat -c %s -- '+q+' && env LD_LIBRARY_PATH=/opt/mgs-postgresql18/usr/lib/x86_64-linux-gnu /opt/mgs-postgresql18/usr/lib/postgresql/18/bin/pg_restore --list '+q+' >/dev/null && printf CATALOGUE_OK'
 facts=transport(meta_command,timeout=180).decode().splitlines();need(len(facts)==3 and facts[0].split()[0]==row['sha256']and int(facts[1])==size and facts[2]=='CATALOGUE_OK','REMOTE_HASH_SIZE_OR_CATALOGUE')
 payload=transport('cat -- '+q,timeout=180);need(isinstance(payload,bytes)and len(payload)==size,'FULL_BINARY_TRANSFER')
 fd=os.memfd_create('mgs-readonly-recovery',flags=0)
 try:
  view=memoryview(payload);offset=0
  while offset<len(view):offset+=os.write(fd,view[offset:offset+1024*1024])
  view.release();del payload;meta=row['metadata'];os.fchown(fd,meta['uid'],meta['gid']);os.fchmod(fd,stat.S_IMODE(meta['mode']));os.utime(fd,ns=(meta['mtime_ns'],meta['mtime_ns']));s=os.fstat(fd);need(s.st_size==size and s.st_uid==meta['uid']and s.st_gid==meta['gid']and stat.S_IMODE(s.st_mode)==stat.S_IMODE(meta['mode'])and s.st_mtime_ns==meta['mtime_ns'],'MATERIALIZED_RAM_METADATA')
  actual=subprocess.check_output(['sha256sum',f'/proc/self/fd/{fd}'],pass_fds=(fd,),text=True).split()[0];need(actual==row['sha256'],'MATERIALIZED_RAM_PAYLOAD_SHA256')
 finally:os.close(fd)
 return {'path':row['path'],'remote_path':remote,'actual_recovered_sha256':actual,'size':size,'full_remote_hash_size_catalogue_validated':True,'real_file_materialized_in_anonymous_RAM':True,'mode_owner_nanosecond_mtime_restored':True,'source_payload_reads':0,'persistent_payload_copies_created':0,'DB_started_or_SQL':False,'at':datetime.datetime.now().astimezone().isoformat()}

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--phase',choices=['pre','post'],default='pre');ap.add_argument('--limit',type=int,default=5);args=ap.parse_args();need(1<=args.limit<=8,'BOUNDED_BATCH');rows=json.load(gzip.open(P/'selected-lineage.json.gz','rt'));need(len(rows)==29 and len({r['path']for r in rows})==29,'EXACT_SELECTED_29')
 out=O/('ram-recovery-'+args.phase+'.jsonl');done={}
 if out.exists():
  for line in out.read_text().splitlines():
   r=json.loads(line);need(r['path']not in done,'DUPLICATE_PROOF');done[r['path']]=r
 need(set(done)<=set(r['path']for r in rows),'PROOF_SCOPE');transport,hashes=bootstrap();batch=[r for r in rows if r['path']not in done][:args.limit]
 for row in batch:
  proof=recover(row,transport)
  with out.open('a')as f:f.write(json.dumps(proof)+'\n');f.flush();os.fsync(f.fileno())
  done[row['path']]=proof
 print(json.dumps({'phase':args.phase,'newly_recovered':len(batch),'verified_total':len(done),'expected':len(rows),'remaining':len(rows)-len(done),'source_payload_reads':0,'persistent_payload_copies':0,'DB_or_SQL':False,'transport_source_hashes_verified':True}))
if __name__=='__main__':main()
