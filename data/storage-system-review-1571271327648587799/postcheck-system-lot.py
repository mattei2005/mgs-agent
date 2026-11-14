"""Validate the landed approved mutation; never purge/delete/rewrite frozen artifacts."""
import pathlib,json,gzip,subprocess,importlib.util,sys,os,stat,datetime,tarfile,hashlib
sys.dont_write_bytecode=True
OUT=pathlib.Path(__file__).parent;spec=importlib.util.spec_from_file_location('frozen_lot',OUT/'system-lot.py');assert spec and spec.loader;lot=importlib.util.module_from_spec(spec);spec.loader.exec_module(lot);m=json.load(open(OUT/'system-lot.json'));assert lot.sha(OUT/'system-lot.json')=='3181fa69cc038fff1ea409892b4d9bcc9099656637d5258ce31f0907b70eb00f';assert lot.sha(OUT/'system-lot.py')==m['executor_sha256']
# Original common gates execute before its overbroad all-payload-absent assertion.
try:lot.verify(m,post=True)
except AssertionError as exc:assert str(exc)=='old kernel payload remains',str(exc)
else:raise AssertionError('Expected historical shared-alias diagnostic no longer applies; reconcile before accepting')
rows=json.load(gzip.open(m['kernel_metadata'],'rt'));remaining=[r for r in rows if os.path.lexists(r['path'])];assert len(remaining)==1 and remaining[0]['path']=='/lib','unexplained payload residue'
r=remaining[0];assert stat.S_ISLNK(os.lstat('/lib').st_mode)and os.readlink('/lib')=='usr/lib'and lot.metadata('/lib')==r,'shared usr-merge alias changed'
ownership=subprocess.check_output(['dpkg-query','-S','/lib'],text=True);assert 'base-files'in ownership and all(p['name']+','not in ownership and p['name']+':'not in ownership for p in m['packages'])
assert all(not os.path.lexists(p)for p in m['kernel_payload_roots']),'retired version root remains'
grub=pathlib.Path('/boot/grub/grub.cfg').read_text();assert all(v not in grub for v in m['retired_kernel_versions'])and all(v in grub for v in m['retained_kernel_versions']);assert not subprocess.check_output(['dpkg','--audit'],text=True).strip()
before=json.load(open(OUT/'execution-before.json'))
for name,version in before['auxiliary_tools'].items():assert lot.installed_package(name)==version,'out-of-scope tools changed'
journal=[json.loads(s)for s in (OUT/'system-file-journal.jsonl').read_text().splitlines()];assert len(journal)==len(m['file_targets'])and len({r['path']for r in journal})==len(journal)and {r['path']for r in journal}=={r['path']for r in m['file_targets']};assert all(not os.path.lexists(r['path'])for r in m['file_targets'])
sec=pathlib.Path('/root/.hermes/secure-backups/storage-system-review-1571271327648587799');native=(sec/'kernel-purge.stdout').read_text();removed=[s.split()[1]for s in native.splitlines()if s.startswith('Removing ')];assert len(removed)==len(m['packages'])and set(removed)=={p['name']for p in m['packages']};assert not any(s.startswith('Setting up ')for s in native.splitlines())
# Exercise only retained DEBs after original payload roots are absent; no extraction/install.
recovery=[]
for pkg in m['rollback_packages']:
 assert lot.sha(pkg['path'])==pkg['sha256'];p=subprocess.Popen(['dpkg-deb','--fsys-tarfile',pkg['path']],stdout=subprocess.PIPE,stderr=subprocess.PIPE);assert p.stdout is not None;members=0;regular=0;h=hashlib.sha256()
 with tarfile.open(fileobj=p.stdout,mode='r|')as tf:
  for member in tf:
   members+=1;h.update(member.name.encode()+b'\0')
   if member.issym():h.update(member.linkname.encode())
   elif member.islnk():h.update(member.linkname.encode())
   elif member.isfile():
    regular+=1;stream=tf.extractfile(member);assert stream is not None;size=0
    while chunk:=stream.read(1024*1024):size+=len(chunk);h.update(chunk)
    assert size==member.size
   else:raise AssertionError('unexpected reconstructed member type')
 while p.stdout.read(1024*1024):pass
 p.stdout.close();err=p.stderr.read()if p.stderr else b'';assert p.wait()==0,err.decode(errors='replace');assert members==pkg['members_verified'];recovery.append({'package':pkg['package'],'archive_sha256_unchanged':True,'members_read':members,'regular_payloads_read':regular,'retained_stream_digest':h.hexdigest()})
current=[]
for b in before['filesystems']:
 s=os.statvfs(b['mount']);used=(s.f_blocks-s.f_bfree)*s.f_frsize;avail=s.f_bavail*s.f_frsize;current.append({'mount':b['mount'],'used_bytes':used,'available_bytes':avail,'used_percent':round(used/(used+avail)*100,2),'available_delta_bytes':avail-b['available_bytes']})
r={'status':'PASS','confirmation_message_id':'1571285972589477891','manifest_sha256':lot.sha(OUT/'system-lot.json'),'frozen_executor_sha256':lot.sha(OUT/'system-lot.py'),'frozen_executor_not_modified_or_reexecuted':True,'frozen_executor_historical_postcheck':'failed only because shared /lib usr-merge infrastructure alias was included as an absence witness, not a native disposal action','usrmerge_shared_alias_preserved_unchanged':True,'removed_kernel_packages':removed,'download_files_absent':len(journal),'retired_payload_nodes_absent':len(rows)-len(remaining),'shared_infrastructure_witnesses_retained':len(remaining),'old_version_roots_absent':len(m['kernel_payload_roots']),'rollback_readback':recovery,'rollback_reinstallation_or_boot_exercised':False,'out_of_scope_auxiliary_tools_preserved':len(before['auxiliary_tools']),'protected_hashes_verified':len(m['protected_hashes']),'gateway_pids_unchanged':True,'boot_identity_unchanged':True,'no_new_native_installs':True,'filesystems':current,'observed_global_available_delta_bytes':sum(x['available_delta_bytes']for x in current),'delta_not_exclusive_attribution':True,'parent_review_complete':False,'checked_at':datetime.datetime.now().astimezone().isoformat()};(OUT/'system-post-validation.json').write_text(json.dumps(r,indent=2)+'\n');lot.audit({'action':'system_retirement_postcheck_usrmerge_witness_reconciled_completed','confirmation_message_id':'1571285972589477891','manifest_sha256':r['manifest_sha256'],'removed_packages':len(removed),'download_files_absent':len(journal),'shared_alias_preserved':'/lib','evidence':str(OUT/'system-post-validation.json')});print(json.dumps({k:v for k,v in r.items()if k!='rollback_readback'}))
