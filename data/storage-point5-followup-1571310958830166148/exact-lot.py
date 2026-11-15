"""Exact follow-up lot: 4 obsolete tools + 11 byte-duplicate intermediates. Read-only by default."""
import pathlib,json,subprocess,os,sys,importlib.util,gzip,datetime,argparse,stat
sys.dont_write_bytecode=True
OUT=pathlib.Path(__file__).parent;ROOT=pathlib.Path('/root/mgs-agent');SEC=pathlib.Path('/root/.hermes/secure-backups/storage-point5-followup-1571310958830166148')
DEP=ROOT/'data/storage-system-review-1571271327648587799/system-lot.py'
spec=importlib.util.spec_from_file_location('metadata_lib',DEP);assert spec and spec.loader;lib=importlib.util.module_from_spec(spec);spec.loader.exec_module(lib)
spec2=importlib.util.spec_from_file_location('retained_reader',OUT/'read-retained-intermediates.py');assert spec2 and spec2.loader;reader=importlib.util.module_from_spec(spec2);spec2.loader.exec_module(reader)
EXPECTED={'linux-tools-6.8.0-138','linux-tools-6.8.0-138-generic','linux-tools-6.8.0-142','linux-tools-6.8.0-142-generic'}
BASE=pathlib.Path('/root/zeus-vps-maintenance-1565730926233657347/rollback')
def installed(name):
 p=subprocess.run(['dpkg-query','-W','-f=${db:Status-Abbrev}\t${Version}',name],capture_output=True,text=True);return p.stdout.strip()if p.returncode==0 else None
def actions(packages):
 p=subprocess.run(['apt-get','-s','purge','--',*[x['name']for x in packages]],capture_output=True,text=True,timeout=50);assert p.returncode==0;rows=[s.split()for s in p.stdout.splitlines()if s.startswith(('Inst ','Remv ','Purg '))];assert len(rows)==4 and all(s[0]=='Purg'for s in rows)and{s[1]for s in rows}==EXPECTED,'native transaction drift';return rows
def verify(m,post=False):
 assert m['authority_message_id']=='1571310958830166148'and m['owner_id']=='344196393512075265'
 assert m['executor_sha256']==lib.sha(__file__)and m['metadata_library_sha256']==lib.sha(DEP)
 assert m['retained_reader_sha256']==lib.sha(OUT/'read-retained-intermediates.py')
 assert len(m['packages'])==4 and{x['name']for x in m['packages']}==EXPECTED,'package scope drift'
 assert len(m['duplicates'])==11 and len({x['source']for x in m['duplicates']})==11,'duplicate scope drift'
 for x in m['duplicates']:
  p=pathlib.Path(x['source']);assert p.name=='data.tar.gz'and p.parent.parent==BASE and p.resolve()==p,'file scope drift';assert pathlib.Path(x['retained_deb']).parent==p.parent
 for x in m['shared_infrastructure']:assert lib.metadata(x['path'])==x,'structural alias changed'
 assert pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip()==m['boot_id']
 assert subprocess.check_output(['uname','-r'],text=True).strip()==m['running_kernel']
 for name,version in m['protected_package_versions'].items():assert installed(name)==version,'retained package changed'
 for x in m['protected_hashes']:assert lib.sha(x['path'])==x['sha256'],'protected file changed: '+x['path']
 for profile,pid in m['gateway_pids'].items():
  assert subprocess.run(['systemctl','is-active','--quiet',profile+'-gateway.service']).returncode==0
  assert int(subprocess.check_output(['systemctl','show',profile+'-gateway.service','-p','MainPID','--value'],text=True))==pid
 assert not subprocess.check_output(['systemctl','--failed','--no-legend','--plain'],text=True).strip()
 q=subprocess.run(['sha256sum','-c',m['legacy_checksum_manifest']],cwd=BASE.parent,capture_output=True,text=True,timeout=45);assert q.returncode==0,'original retained checksum set broken'
 assert reader.verify(m['duplicates'])['verified']==11
 for x in m['rollback_packages']:
  assert lib.sha(x['path'])==x['sha256']
  for field,value in [('Package',x['package']),('Version',x['version'])]:assert subprocess.check_output(['dpkg-deb','-f',x['path'],field],text=True).strip()==value
  subprocess.run(['dpkg-deb','--fsys-tarfile',x['path']],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,check=True,timeout=25)
 if post:
  assert all(not(installed(x['name'])or'').startswith('ii')for x in m['packages']),'package still installed'
  assert all(not os.path.lexists(x['path'])for x in m['package_metadata']),'version-specific payload remains'
  assert all(not os.path.lexists(x['source'])for x in m['duplicates']),'duplicate remains'
  assert not subprocess.check_output(['dpkg','--audit'],text=True).strip()
 else:
  assert not lib.consumers({'kernel_payload_roots':m['package_roots'],'file_targets':[{'path':x['source']}for x in m['duplicates']]}),'active consumer'
  assert not set(subprocess.check_output(['apt-mark','showhold'],text=True).splitlines())&EXPECTED
  for x in m['packages']:assert installed(x['name'])=='ii \t'+x['version'],'package identity drift'
  for x in m['control_hashes']:assert lib.sha(x['path'])==x['sha256'],'package control drift'
  actual=[lib.metadata(x['path'])for x in m['package_metadata']]+[lib.metadata(x['source'])for x in m['duplicates']]
  assert len(actual)==m['node_count']and lib.fingerprint(actual)==m['node_fingerprint'],'metadata/count drift'
  paths={x['path']for x in m['package_metadata']}
  for root in m['package_roots']:
   assert not os.path.ismount(root)and not pathlib.Path(root).is_symlink()
   for d,dirs,files in os.walk(root,followlinks=False):
    for n in list(dirs):
     p=pathlib.Path(d,n)
     if p.is_symlink():assert str(p)in paths;dirs.remove(n)
    assert all(str(pathlib.Path(d,n))in paths for n in files),'new unclassified payload'
  for x in m['duplicates']:assert lib.sha(x['source'])==x['sha256']and stat.S_ISREG(os.lstat(x['source']).st_mode)
  actions(m['packages'])
 return {'status':'PASS','mode':'post'if post else'preflight','packages':4,'duplicate_files':11,'metadata_nodes':m['node_count'],'retained_byte_readback':True,'deletions_by_validator':0}
def audit(action,extra):
 with (ROOT/'logs/events-audit.jsonl').open('a')as f:f.write(json.dumps(dict(at=datetime.datetime.now().astimezone().isoformat(),agent='zeus',action=action,thread_id='1569928464033783862',**extra))+'\n');f.flush();os.fsync(f.fileno())
def execute(m):
 a_path=OUT/'approval.json'
 if not a_path.exists():raise RuntimeError('missing_new_owner_confirmation_no_mutation')
 a=json.load(open(a_path));assert a['owner_id']=='344196393512075265'and a['thread_id']=='1569928464033783862'and a['native_readback_verified']is True
 assert a['confirmation_message_id']!=m['authority_message_id']and a['manifest_sha256']==lib.sha(OUT/'deletion-manifest.json')and a['executor_sha256']==lib.sha(__file__)
 verify(m);fd=os.open(OUT/'execution-start.json',os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
 with os.fdopen(fd,'w')as f:json.dump(a,f);f.flush();os.fsync(f.fileno())
 audit('point5_followup_exact_lot_start',{'confirmation_message_id':a['confirmation_message_id'],'manifest_sha256':a['manifest_sha256']})
 try:
  env=dict(os.environ,DEBIAN_FRONTEND='noninteractive',NEEDRESTART_MODE='l');p=subprocess.run(['apt-get','-y','-o','Dpkg::Options::=--force-confold','purge','--',*[x['name']for x in m['packages']]],capture_output=True,text=True,timeout=300,env=env);(SEC/'apt-purge.stdout').write_text(p.stdout);(SEC/'apt-purge.stderr').write_text(p.stderr);assert p.returncode==0,'native purge failed; reconcile effects before retry'
  for x in m['duplicates']:
   assert lib.metadata(x['source'])==x['metadata']and lib.sha(x['source'])==x['sha256'];os.unlink(x['source'])
   with (OUT/'file-journal.jsonl').open('a')as f:f.write(json.dumps({'path':x['source'],'absent':not os.path.lexists(x['source'])})+'\n');f.flush();os.fsync(f.fileno())
  result=verify(m,True);(OUT/'filesystem-result.json').write_text(json.dumps(result,indent=2)+'\n');audit('point5_followup_exact_lot_filesystem_completed',{'confirmation_message_id':a['confirmation_message_id'],'manifest_sha256':a['manifest_sha256']});print(json.dumps(result))
 except Exception as e:audit('point5_followup_exact_lot_partial_failure',{'confirmation_message_id':a['confirmation_message_id'],'error_type':type(e).__name__});raise
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--execute',action='store_true');parser.add_argument('--post',action='store_true');a=parser.parse_args()
 try:
  assert lib.sha(OUT/'deletion-manifest.json')==(OUT/'deletion-manifest.sha256').read_text().split()[0];m=json.load(open(OUT/'deletion-manifest.json'));execute(m)if a.execute else print(json.dumps(verify(m,a.post)))
 except Exception as e:print('BLOCKED: '+str(e),file=sys.stderr);raise SystemExit(1)
