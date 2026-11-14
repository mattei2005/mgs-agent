"""Read-only bounded delivery check; never commits, triggers the watcher or rewrites results."""
import pathlib,subprocess,json,time,datetime,os
ROOT=pathlib.Path('/root/mgs-agent');SCOPE='data/digitaltrust-runtime-migration-1571245557316452364';OUT=ROOT/SCOPE;SEC=pathlib.Path('/root/.hermes/secure-backups/digitaltrust-runtime-migration/1571245557316452364')
def git(*args):return subprocess.run(['git','-C',str(ROOT),*args],capture_output=True,timeout=30)
files=git('ls-files','--cached','--others','--exclude-standard','-z','--',SCOPE).stdout.decode().split('\0');files=sorted(set(x for x in files if x));files+=['scripts/meta-digital-trust-hourly40-run.py','scripts/meta-digital-trust-pc1-create-one.py','context/storage-reorganization-20261112.md','profiles/zeus-skills/ops/vps-maintenance-and-backup-governance/references/backup-retention-scope-and-redundancy.md']
rows=[('data/infra-inventory.json','runtime_artifacts','digitaltrust-runtime-migration-1571245557316452364'),('data/infra-inventory.json','runtime_artifacts','storage-conditional-runtime-review-1571239570069131275'),('data/agent-checkpoints.json','checkpoints','ZEUS-DIGITALTRUST-RUNTIME-MIGRATION-1571245557316452364'),('data/agent-checkpoints.json','checkpoints','ZEUS-STORAGE-CONDITIONAL-RUNTIMES-1571239570069131275')]
start=time.monotonic();deadline=start+230;checks=0
while True:
 fetch=git('fetch','origin','main','--quiet');assert fetch.returncode==0,'Read-only fetch failed; no local write attempted'
 missing=[]
 for p in files:
  remote=git('show','origin/main:'+p)
  if remote.returncode or remote.stdout!=(ROOT/p).read_bytes():missing.append(p)
 parsed=[]
 for path,key,identifier in rows:
  remote=git('show','origin/main:'+path);r=json.loads(remote.stdout)if remote.returncode==0 else {};l=json.load(open(ROOT/path));a=[x for x in l[key]if x.get('id')==identifier];b=[x for x in r.get(key,[])if x.get('id')==identifier];ok=len(a)==1 and a==b;parsed.append({'path':path,'id':identifier,'matched':ok})
  if not ok:missing.append(path+'#'+identifier)
 checks+=1
 if not missing:break
 if time.monotonic()>=deadline:
  print(json.dumps({'status':'native_batch_pending','mismatches':missing,'elapsed_seconds':round(time.monotonic()-start,1),'checks':checks}));raise SystemExit(2)
 time.sleep(min(20,max(0,deadline-time.monotonic())))
head=git('rev-parse','HEAD').stdout.decode().strip();origin=git('rev-parse','origin/main').stdout.decode().strip();assert head==origin
result=json.load(open(OUT/'result.json'));digest=subprocess.check_output(['sha256sum',str(OUT/'result.json')],text=True).split()[0];assert digest==(OUT/'result.sha256').read_text().split()[0]
for profile,pid in result['gateway_pids_unchanged'].items():
 assert int(subprocess.check_output(['systemctl','show',profile+'-gateway.service','-p','MainPID','--value'],text=True).strip())==pid
 assert subprocess.run(['systemctl','is-active','--quiet',profile+'-gateway.service']).returncode==0
for row in result['changed_scripts']:
 assert subprocess.check_output(['sha256sum',row['path']],text=True).split()[0]==row['after_sha256']
 assert subprocess.check_output(['sha256sum',row['backup']],text=True).split()[0]==row['before_sha256']
for label in ['46904a3b','ad2d4822']:assert (pathlib.Path('/root/.hermes')/('hermes-agent-port-main-'+label+'-mgs')).is_dir()
receipt={'status':'PASS','remote_commit':origin,'artifacts_checked':len(files),'parsed_records':parsed,'result_sha256':digest,'mismatches':[],'gateway_pids_still_unchanged':True,'old_roots_present':2,'elapsed_seconds':round(time.monotonic()-start,1),'native_batch_checks':checks,'verified_at':datetime.datetime.now().astimezone().isoformat()};p=SEC/'git-delivery-receipt.json';p.write_text(json.dumps(receipt,indent=2)+'\n');assert json.loads(p.read_text())==receipt
print(json.dumps({'delivery':receipt,'receipt':str(p)},ensure_ascii=False))
