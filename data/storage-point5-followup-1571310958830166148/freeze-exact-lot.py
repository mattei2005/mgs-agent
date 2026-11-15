"""Freeze the proven follow-up scope; no uninstall/deletion and no approval creation."""
import pathlib,json,os,sys,subprocess,importlib.util,gzip,time,datetime,collections
sys.dont_write_bytecode=True
OUT=pathlib.Path(__file__).parent;SEC=pathlib.Path('/root/.hermes/secure-backups/storage-point5-followup-1571310958830166148');assert not(OUT/'deletion-manifest.json').exists()
spec=importlib.util.spec_from_file_location('lot',OUT/'exact-lot.py');assert spec and spec.loader;lot=importlib.util.module_from_spec(spec);spec.loader.exec_module(lot);lib=lot.lib;review=json.load(open(OUT/'candidate-review.json'));saved=json.load(gzip.open(SEC/'candidate-node-metadata.json.gz','rt'));rows={x['path']:x for x in saved};dups=json.load(open(OUT/'intermediate-duplicate-proof.json'))['rows'];rollback=json.load(open(OUT/'auxiliary-rollback.json'));assert rollback['status']=='PASS'
for x in dups:x['metadata']=rows[x['source']]
pkg=[x for x in saved if x['path']not in{x['source']for x in dups}];assert len(pkg)==54 and all(any(v in x['path']for v in ['6.8.0-138','6.8.0-142'])for x in pkg)
for i in range(2):
 actual=[lib.metadata(x['path'])for x in saved];assert lib.fingerprint(actual)==lib.fingerprint(saved)
 if i==0:time.sleep(2)
old=json.load(open('/root/mgs-agent/data/storage-system-review-1571271327648587799/system-lot.json'));protected=[{'path':x['path'],'sha256':lib.sha(x['path'])}for x in old['protected_hashes']];protected.extend({'path':str(p),'sha256':lib.sha(p)}for p in [pathlib.Path('/usr/bin/perf'),pathlib.Path('/usr/lib/linux-tools/6.8.0-147-generic/perf')]);base=pathlib.Path('/root/zeus-vps-maintenance-1565730926233657347')
for p in ['rollback.sha256','backup-result.json','install-result.json','prestate.json','system-config.tgz']:protected.append({'path':str(base/p),'sha256':lib.sha(base/p)})
controls=[]
for x in review['packages']:
 for suffix in ['list','md5sums','preinst','postinst','prerm','postrm','triggers']:
  p=pathlib.Path('/var/lib/dpkg/info')/(x['name']+'.'+suffix)
  if p.is_file():controls.append({'path':str(p),'sha256':lib.sha(p)})
inodes={}
for x in saved:
 key=(x['dev'],x['ino']);v=inodes.setdefault(key,dict(x,count=0));v['count']+=1
potential=sum(x['allocated']for x in inodes.values()if x['count']>=x['nlink']);created=0;seen=set()
for base2 in [OUT,SEC]:
 for d,ds,fs in os.walk(base2,followlinks=False):
  for n in fs:
   s=os.lstat(pathlib.Path(d,n));key=(s.st_dev,s.st_ino)
   if key not in seen:seen.add(key);created+=s.st_blocks*512
m={'status':'frozen_waiting_new_critical_confirmation','owner_id':'344196393512075265','thread_id':'1569928464033783862','authority_message_id':'1571310958830166148','packages':review['packages'],'duplicates':dups,'package_metadata':pkg,'package_roots':json.load(open('/root/mgs-agent/data/storage-system-review-1571271327648587799/next-point5-review.json'))['version_specific_roots'],'node_count':len(saved),'node_fingerprint':lib.fingerprint(saved),'executor_sha256':lib.sha(OUT/'exact-lot.py'),'metadata_library_sha256':lib.sha(lot.DEP),'retained_reader_sha256':lib.sha(OUT/'read-retained-intermediates.py'),'control_hashes':controls,'protected_hashes':protected,'protected_package_versions':{name:lot.installed(name)for name in old['protected_package_versions']},'gateway_pids':{p:int(subprocess.check_output(['systemctl','show',p+'-gateway.service','-p','MainPID','--value'],text=True))for p in ['zeus','ares','atena']},'boot_id':pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'running_kernel':subprocess.check_output(['uname','-r'],text=True).strip(),'shared_infrastructure':[lib.metadata(p)for p in ['/lib','/bin','/sbin','/lib64']if pathlib.Path(p).is_symlink()],'legacy_checksum_manifest':str(base/'rollback.sha256'),'rollback_packages':rollback['packages'],'potential_file_reclaim_bytes':potential,'analysis_and_preservation_bytes_at_freeze':created,'estimated_net_bytes':potential-created,'future_git_growth_and_directory_blocks_excluded':True,'no_autoremove_or_restart_or_reboot':True,'original_backup_root_and_all12_checksum_entries_preserved':True,'backup_limitation':'Reconstructed tool DEBs read/hash/link roundtrip and local dependency simulation passed; actual package reinstallation not executed. Duplicate bytes are independently readable from surviving DEB members.','created_at':datetime.datetime.now().astimezone().isoformat()};(OUT/'deletion-manifest.json').write_text(json.dumps(m,indent=2)+'\n');digest=lib.sha(OUT/'deletion-manifest.json');(OUT/'deletion-manifest.sha256').write_text(digest+'  deletion-manifest.json\n');print(json.dumps({'manifest_sha256':digest,'packages':len(m['packages']),'duplicate_files':len(dups),'metadata_nodes':len(saved),'potential_reclaim_bytes':potential,'analysis_created_bytes':created,'net_estimate_bytes':potential-created,'net_estimate_MiB':round((potential-created)/1024**2,2),'approval_exists':(OUT/'approval.json').exists(),'execution_started':(OUT/'execution-start.json').exists()}))
