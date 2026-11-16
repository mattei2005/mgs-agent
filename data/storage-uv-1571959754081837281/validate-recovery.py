"""Independent read-only validation after exact recovery of excess cache entries."""
import pathlib,json,gzip,os,stat,subprocess,collections,importlib.util,datetime
OUT=pathlib.Path(__file__).parent;PRIVATE=pathlib.Path('/root/.hermes/secure-backups/storage-uv-1571959754081837281');CACHE=pathlib.Path('/root/.cache/uv')
spec=importlib.util.spec_from_file_location('UV_post_recovery_readonly',OUT/'prune-gate.py');assert spec and spec.loader;g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
m,rows=g.load();targets,chosen=g.scope(m,rows);original={x['relative']:x for x in rows};current,_=g.c.snapshot(None);actual={x['relative']:x for x in current};kept={p:r for p,r in original.items()if not g.selected(p,targets)}
assert set(actual)==set(kept),'Net cache path scope differs after recovery'
restored=set(json.load(open(OUT/'postcheck-path-difference.json'))['missing']);assert len(restored)==45
approved_ancestors={'.'}
for t in targets:
 p=pathlib.PurePosixPath(t).parent
 while str(p)!='.':approved_ancestors.add(str(p));p=p.parent
repair_parents=set()
for r in restored:
 p=pathlib.PurePosixPath(r).parent
 while str(p)!='.':
  if str(p)not in restored:repair_parents.add(str(p))
  p=p.parent
deleted_links=collections.Counter((r['dev'],r['ino'])for r in chosen if r['kind']=='file');replaced_inodes=0
for rel,before in kept.items():
 after=actual[rel];expect=dict(before);ignore=set()
 if rel in restored:
  ignore={'dev','ino','ctime_ns'}
  if before['kind']=='directory':ignore|={'size','allocated','nlink'}
  if before['ino']!=after['ino']:replaced_inodes+=1
 elif before['kind']=='directory'and rel in approved_ancestors:ignore={'size','allocated','nlink','mtime_ns','ctime_ns'}
 elif before['kind']=='directory'and rel in repair_parents:ignore={'ctime_ns'}
 elif before['kind']=='file'and deleted_links[(before['dev'],before['ino'])]:expect['nlink']-=deleted_links[(before['dev'],before['ino'])];ignore={'ctime_ns'}
 assert {k:v for k,v in after.items()if k not in ignore}=={k:v for k,v in expect.items()if k not in ignore},'Unexpected post-recovery metadata: '+rel
expected=json.load(gzip.open(m['retained_payload_index'],'rt'));assert len(expected)==63046 and g.payload_hashes(list(expected))==expected
managed_hashes=json.load(open(PRIVATE/'managed-cache-before-sha256.json'));assert g.payload_hashes(list(managed_hashes))==managed_hashes
managed=pathlib.Path('/root/.hermes/cache/uv');managed_before=json.load(open(PRIVATE/'managed-cache-before-metadata.json'));managed_after={}
for d,ds,fs in os.walk(managed,followlinks=False):
 for n in ds+fs:
  p=pathlib.Path(d)/n;s=os.lstat(p);kind='file'if stat.S_ISREG(s.st_mode)else'directory'if stat.S_ISDIR(s.st_mode)else'link'if stat.S_ISLNK(s.st_mode)else'other';row=dict(kind=kind,dev=s.st_dev,ino=s.st_ino,mode=stat.S_IMODE(s.st_mode),uid=s.st_uid,gid=s.st_gid)
  if kind=='file':row.update(size=s.st_size,mtime_ns=s.st_mtime_ns)
  if kind=='link':row['target']=os.readlink(p)
  managed_after[str(p.relative_to(managed))]=row
assert managed_after==managed_before
controls=json.load(open(OUT/'retirement-controls-before.json'));assert all(g.sha(p)==h for p,h in controls.items())
availability=json.load(open(OUT/'post-recovery-availability.json'));assert availability['configs_passed']==availability['smokes_passed']==3
runtime=g.runtime();pre=json.loads(json.load(open(OUT/'approval-preflight-1571969258986938601.json'))['stdout'])['runtime'];assert runtime==pre
failed=subprocess.check_output(['systemctl','--failed','--no-legend','--plain'],text=True);assert not failed.strip()
native=json.load(open(OUT/'prune-native-result.json'));s=os.statvfs('/');used=(s.f_blocks-s.f_bfree)*s.f_frsize;available=s.f_bavail*s.f_frsize
result=dict(status='PASS_RECOVERED_SCOPE_DEVIATION',original_frozen_gate_postcheck_did_not_pass=True,original_gate_or_manifest_modified=False,native_prune_calls=1,native_exit_code=native['exit_code'],approved_targets_absent=193,approved_removed_node_counts=m['target_node_counts'],unplanned_removed_node_counts=dict(file=30,directory=12,link=3),unplanned_nodes_restored=45,unplanned_regular_files_SHA256_restored=30,three_wheels_reconstructed_to_original_SHA256=True,restored_original_inode_numbers_not_claimed=True,restored_nodes_with_different_inode=replaced_inodes,remaining_cache_nodes=len(actual),retained_cache_payloads_verified=63046,managed_cache_payloads_verified=len(managed_hashes),managed_cache_metadata_unchanged=True,profile_controls_unchanged=6,profile_configs_passed=3,profile_smokes_passed=3,failed_units=0,runtime_unchanged=True,runtime=runtime,native_interval_global_delta_bytes=native['observed_global_delta_bytes'],post_recovery_global_delta_from_native_before_bytes=available-native['before']['available'],disk_used_percent=round(used/(used+available)*100,2),available_GiB=round(available/1024**3,2),native_logical_counter_not_physical_savings=True,exact_old_approved_environments_not_restored_by_design=True,new_cron_or_retention=False,whole_disk_review_complete=False,at=datetime.datetime.now().astimezone().isoformat())
(OUT/'recovery-post-validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
