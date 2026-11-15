"""Exact archive-backed disposal, read-only until new owner confirmation."""
import pathlib,json,subprocess,os,sys,importlib.util,tarfile,hashlib,argparse,shutil,datetime,stat
sys.dont_write_bytecode=True
OUT=pathlib.Path(__file__).parent;ROOT=pathlib.Path('/root/mgs-agent');DEP=ROOT/'data/storage-system-review-1571271327648587799/system-lot.py';spec=importlib.util.spec_from_file_location('lib',DEP);assert spec and spec.loader;lib=importlib.util.module_from_spec(spec);spec.loader.exec_module(lib)
TREE='/root/mgs-agent-backups/wp-file-manager-openzed/20260819T184628-0400/wp-file-manager';FILE='/root/zeus-vps-maintenance-1565730926233657347/original-vendor-debs/monarx-agent_4.3.82-master_amd64.deb'
def nodes():
 rows=[lib.metadata(TREE),lib.metadata(FILE)]
 for d,dirs,files in os.walk(TREE,followlinks=False):
  for name in dirs+files:rows.append(lib.metadata(pathlib.Path(d,name)))
 return rows
def retained(m):
 for x in m['recovery_hashes']:assert lib.sha(x['path'])==x['sha256'],'recovery input drift'
 p=subprocess.run(['python3',m['site_reader']],capture_output=True,text=True,timeout=90);assert p.returncode==0,'site recovery reader failed';site=json.loads(p.stdout);assert site['counts']['files']==948
 found=False
 with tarfile.open(m['historical_archive'],'r|xz')as tf:
  for member in tf:
   if member.name==m['historical_member']:
    stream=tf.extractfile(member);assert stream is not None;h=hashlib.sha256();size=0
    while chunk:=stream.read(1024*1024):h.update(chunk);size+=len(chunk)
    assert h.hexdigest()==m['historical_member_sha256']and size==m['historical_member_size'];found=True;break
 assert found,'historical retained member missing'
 return {'site_files_verified':site['counts']['files'],'historical_vendor_member_verified':True,'original_target_payloads_read':0}
def verify(m,post=False):
 assert m['owner_id']=='344196393512075265'and m['authority_message_id']=='1571327506374598789'
 assert m['executor_sha256']==lib.sha(__file__)and m['metadata_library_sha256']==lib.sha(DEP)
 assert len(m['targets'])==2 and m['targets']==[{'path':TREE,'action':'delete_tree'},{'path':FILE,'action':'delete_file'}],'scope drift'
 assert pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip()==m['boot_id']
 for x in m['protected_hashes']:assert lib.sha(x['path'])==x['sha256'],'protected content drift'
 for profile,pid in m['gateway_pids'].items():
  assert subprocess.run(['systemctl','is-active','--quiet',profile+'-gateway.service']).returncode==0
  assert int(subprocess.check_output(['systemctl','show',profile+'-gateway.service','-p','MainPID','--value'],text=True))==pid
 assert not subprocess.check_output(['systemctl','--failed','--no-legend','--plain'],text=True).strip()
 if post:assert not os.path.lexists(TREE)and not os.path.lexists(FILE),'target still present'
 else:
  assert pathlib.Path(TREE).is_dir()and not pathlib.Path(TREE).is_symlink()and not os.path.ismount(TREE)
  assert pathlib.Path(FILE).is_file()and not pathlib.Path(FILE).is_symlink()and not os.path.ismount(FILE)
  assert str(pathlib.Path(TREE).resolve())==TREE and str(pathlib.Path(FILE).resolve())==FILE
  actual=nodes();assert all(x['dev']==os.stat(TREE).st_dev and not os.path.ismount(x['path'])for x in actual),'mount boundary drift';assert len(actual)==m['node_count']and lib.fingerprint(actual)==m['node_fingerprint'],'metadata/count drift'
  assert not lib.consumers({'kernel_payload_roots':[TREE],'file_targets':[{'path':FILE}]}),'active consumer'
 proof=retained(m)
 return dict(status='PASS',mode='post'if post else'preflight',targets=2,regular_files=m['regular_files'],directories=m['directories'],deletions_by_verifier=0,**proof)
def audit(action,data):
 with(ROOT/'logs/events-audit.jsonl').open('a')as f:f.write(json.dumps(dict(at=datetime.datetime.now().astimezone().isoformat(),agent='zeus',thread_id='1569928464033783862',action=action,**data))+'\n');f.flush();os.fsync(f.fileno())
def execute(m):
 if not(OUT/'approval.json').exists():raise RuntimeError('missing_new_critical_confirmation_no_mutation')
 a=json.load(open(OUT/'approval.json'));assert a['owner_id']=='344196393512075265'and a['thread_id']=='1569928464033783862'and a['native_readback_verified']is True;assert a['confirmation_message_id']!=m['authority_message_id']and a['manifest_sha256']==lib.sha(OUT/'deletion-manifest.json')and a['executor_sha256']==lib.sha(__file__)
 verify(m);fd=os.open(OUT/'execution-start.json',os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
 with os.fdopen(fd,'w')as f:json.dump(a,f);f.flush();os.fsync(f.fileno())
 audit('backup_remainder_exact_lot_start',{'confirmation_message_id':a['confirmation_message_id'],'manifest_sha256':a['manifest_sha256']})
 try:
  for x in m['targets']:
   if x['action']=='delete_tree':shutil.rmtree(x['path'])
   else:os.unlink(x['path'])
   assert not os.path.lexists(x['path'])
   with(OUT/'execution-journal.jsonl').open('a')as f:f.write(json.dumps(dict(x,absent=True))+'\n');f.flush();os.fsync(f.fileno())
  result=verify(m,True);(OUT/'filesystem-result.json').write_text(json.dumps(result,indent=2)+'\n');audit('backup_remainder_exact_lot_filesystem_completed',{'confirmation_message_id':a['confirmation_message_id'],'manifest_sha256':a['manifest_sha256']});print(json.dumps(result))
 except Exception as e:audit('backup_remainder_exact_lot_partial_failure',{'confirmation_message_id':a['confirmation_message_id'],'error_type':type(e).__name__});raise
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--execute',action='store_true');p.add_argument('--post',action='store_true');a=p.parse_args()
 try:
  assert lib.sha(OUT/'deletion-manifest.json')==(OUT/'deletion-manifest.sha256').read_text().split()[0];m=json.load(open(OUT/'deletion-manifest.json'));execute(m)if a.execute else print(json.dumps(verify(m,a.post)))
 except Exception as e:print('BLOCKED: '+str(e),file=sys.stderr);raise SystemExit(1)
