"""Freeze disclosed system-lot candidates, never remove/install anything."""
import pathlib,os,json,gzip,subprocess,importlib.util,collections,datetime,sys
sys.dont_write_bytecode=True
OUT=pathlib.Path(__file__).parent;SEC=pathlib.Path('/root/.hermes/secure-backups/storage-system-review-1571271327648587799');assert not(OUT/'system-lot.json').exists(),'reconcile existing freeze instead of overwriting'
spec=importlib.util.spec_from_file_location('lot',OUT/'system-lot.py');assert spec is not None and spec.loader is not None;lot=importlib.util.module_from_spec(spec);spec.loader.exec_module(lot)
c=json.load(open(OUT/'system-candidate.json'));s=json.load(open(OUT/'system-state.json'));rollback=json.load(open(OUT/'kernel-rollback.json'));go=json.load(open(OUT/'go-installer-proof.json'));assert not c['unrecognized_unowned_files']and not c['custom_executable_or_boot_policy_references'];assert rollback['status']=='PASS'and rollback['packages_verified']==8
q=subprocess.run(['dpkg','--verify',*[p['name']for p in c['packages']]],capture_output=True,text=True,timeout=90);assert q.returncode==0 and not q.stdout.strip(),'installed package verification failure'
files=[]
for p in [*[r['path']for r in c['cached_debs']],go['archive']]:
 r=lot.metadata(p);assert not pathlib.Path(p).is_symlink();files.append({'path':p,'metadata':r,'sha256':lot.sha(p),'origin':'pre_existing_residue','kind':'cached_deb'if p.endswith('.deb')else'installed_go_download_cache'})
ledger=str(SEC/'old-kernel-payload-metadata.json.gz');kernel=json.load(gzip.open(ledger,'rt'));assert len(kernel)==c['payload_file_or_link_count'];assert lot.fingerprint(kernel)==lot.fingerprint([lot.metadata(r['path'])for r in kernel])
protected=list(c['protected_boot_files']);extra=[]
for root in ['/boot/efi','/etc/kernel/postrm.d','/etc/apt/apt.conf.d']:
 extra.extend(p for p in pathlib.Path(root).rglob('*')if p.is_file()and not p.is_symlink())
for p in ['/etc/default/grub','/usr/sbin/needrestart','/usr/lib/needrestart/apt-pinvoke','/root/.local/share/mgs-router-toolchain/go/bin/go','/root/mgs-agent/scripts/meta-digital-trust-hourly40-run.py','/root/mgs-agent/scripts/meta-digital-trust-pc1-create-one.py']:
 if pathlib.Path(p).is_file():extra.append(pathlib.Path(p))
for profile in ['zeus','ares','atena']:
 p=pathlib.Path('/root/.hermes/profiles')/profile/'config.yaml'
 if p.is_file():extra.append(p)
for p in sorted(set(extra)):protected.append({'path':str(p),'sha256':lot.sha(p)})
protected_versions={p['name']:p['version']for p in s['packages']if p['status'].startswith('ii')and any(v.removesuffix('-generic')in p['name']for v in c['protected_running_prior_and_pending_kernels'])};assert len(protected_versions)>=12
pre=[]
for p in c['packages']:
 for suffix in ['list','md5sums','preinst','postinst','prerm','postrm','triggers']:
  path=pathlib.Path('/var/lib/dpkg/info')/(p['name']+'.'+suffix)
  if path.is_file():pre.append({'path':str(path),'sha256':lot.sha(path)})
# Credit each inode only when all its links are inside this exact lot.
inodes={}
for r in kernel+[r['metadata']for r in files]:
 k=(r['dev'],r['ino']);v=inodes.setdefault(k,dict(r,count=0));v['count']+=1
bydev=collections.Counter()
for r in inodes.values():
 if r['count']>=r['nlink']:bydev[str(r['dev'])]+=r['allocated']
created=0;seen=set()
for base in [SEC,OUT]:
 for directory,dirs,names in os.walk(base,followlinks=False):
  for name in names:
   p=pathlib.Path(directory,name);t=p.lstat();key=(t.st_dev,t.st_ino)
   if key not in seen:seen.add(key);created+=t.st_blocks*512
m={'schema_version':1,'status':'frozen_waiting_new_owner_critical_confirmation','owner_id':'344196393512075265','thread_id':'1569928464033783862','preparation_authority':'1571271327648587799','created_at':datetime.datetime.now().astimezone().isoformat(),'executor_sha256':lot.sha(OUT/'system-lot.py'),'packages':c['packages'],'file_targets':files,'kernel_metadata':ledger,'kernel_metadata_sha256':lot.sha(ledger),'kernel_fingerprint':lot.fingerprint(kernel),'kernel_payload_count':len(kernel),'kernel_payload_roots':c['payload_roots'],'generated_kernel_metadata':c['recognized_generated_module_metadata'],'retired_kernel_versions':c['kernel_versions_to_retire'],'retained_kernel_versions':c['protected_running_prior_and_pending_kernels'],'running_kernel':subprocess.check_output(['uname','-r'],text=True).strip(),'boot_id':pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'protected_package_versions':protected_versions,'protected_hashes':protected,'pre_mutation_hashes':pre,'rollback_packages':rollback['packages'],'gateway_pids':{profile:int(subprocess.check_output(['systemctl','show',profile+'-gateway.service','-p','MainPID','--value'],text=True).strip())for profile in ['zeus','ares','atena']},'potential_file_reclaim_by_device':dict(bydev),'potential_file_reclaim_bytes':sum(bydev.values()),'new_analysis_and_rollback_allocated_at_freeze':created,'estimated_net_from_start_of_this_review':sum(bydev.values())-created,'estimate_excludes_directory_blocks_and_future_git_growth':True,'native_side_effects':['dpkg/APT installed-package metadata update','regenerated GRUB menu removing only retired versions','removal of retired initramfs files','cleanup of exactly listed generated module metadata and now-empty retired module roots'],'service_restart_mode':'NEEDRESTART_MODE=l','no_autoremove':True,'no_reboot':True,'source_rollback_limitation':'Reconstructed installed-payload DEBs: every file/link was roundtrip-verified and local reinstall dependency simulation passed; actual package reinstallation/boot was not exercised. Retained active/fallback/pending kernels remain unchanged.'}
(OUT/'system-lot.json').write_text(json.dumps(m,indent=2)+'\n');digest=lot.sha(OUT/'system-lot.json');(OUT/'system-lot.sha256').write_text(digest+'  system-lot.json\n');print(json.dumps({'manifest_sha256':digest,'packages':len(m['packages']),'download_files':len(files),'payload_nodes':len(kernel),'gross_bytes':m['potential_file_reclaim_bytes'],'new_analysis_and_rollback_bytes':created,'estimated_net_bytes':m['estimated_net_from_start_of_this_review'],'retained_package_versions':len(protected_versions),'protected_hashes':len(protected),'approval_exists':(OUT/'system-approval.json').exists(),'execution_marker_exists':(OUT/'system-execution-start.json').exists()}))
