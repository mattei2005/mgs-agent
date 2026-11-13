import sys, os, json, gzip, subprocess, stat, datetime, hashlib
from pathlib import Path
sys.dont_write_bytecode=True
import review as m
inv=json.load(open(m.D/'inventory.json'));frozen=json.load(gzip.open(m.D/'original-fingerprints.json.gz','rt'))
results=[]
for profile in ['root','zeus','atena','ares']:
 result=json.load(open(m.D/('sqlite-'+profile+'.json')));assert result['snapshot_count']==3 and len(result['snapshots'])==3;results.extend(result['snapshots'])
assert len(results)==12 and len({r['id'] for r in results})==12
assert {r['id'] for r in results}=={r['id'] for r in inv['snapshots']}
proof=json.load(gzip.open(m.PRIOR/'control-plane-archive-proof.json.gz','rt'))
assert m.sha(proof['retained_archive'])==proof['retained_archive_sha256']
archive_map={r['member']:r for r in proof['matched']}
contracts=json.load(gzip.open(m.D/'evidence-coupling.json.gz','rt'));assert sum(not e['matches'] for r in contracts for e in r['contracts'])==0
preservation=[];configs=[]
for snap in frozen:
 root=Path(snap['root']);assert root.is_dir() and not root.is_symlink()
 expected={r['path']:r for r in snap['files']+snap['directories']+snap['links']};seen={}
 for parent,ds,ns in os.walk(root,followlinks=False):
  for n in ds+ns:
   p=Path(parent)/n;s=p.lstat();seen[str(p)]=s
 assert set(expected)==set(seen),'SNAPSHOT_NODESET_CHANGED'
 files=snap['files']
 for start in range(0,len(files),128):
  batch=files[start:start+128];text=subprocess.check_output(['sha256sum','--',*[r['path'] for r in batch]],text=True);hashes={s.split(None,1)[1].lstrip('* '):s.split(None,1)[0] for s in text.splitlines()}
  for r in batch:assert hashes[r['path']]==r['sha256'],'ORIGINAL_HASH_CHANGED'
 for path,r in expected.items():
  s=seen[path]
  assert (s.st_ino,s.st_dev,s.st_size,s.st_mtime_ns,s.st_mode,s.st_blocks*512,s.st_nlink)==tuple(r[k] for k in ['ino','dev','size','mtime_ns','mode','blocks','nlink']),'ORIGINAL_METADATA_CHANGED'
  if stat.S_ISLNK(s.st_mode):assert os.readlink(path)==r['link_target']
 preservation.append({'id':snap['id'],'regular_file_hashes_verified':len(files),'all_nodes_and_metadata_unchanged':True,'original_sidecars_unchanged':True})
 profile=snap['id'].split('-',1)[1];matched=0;unmatched={}
 root_keep=Path(next(r['root'] for r in frozen if r['id']=='recovery-root'))
 for r in files:
  rel=r['rel'];is_db=rel=='state.db' or rel.startswith('state.db-')
  if is_db:continue
  normalized='skills/'+rel[len('skills-tree/'):] if rel.startswith('skills-tree/') else rel
  candidate=m.KEEP/'retry-1/cutover-checkpoints'/profile/normalized
  kept=root_keep/rel if profile=='root' else candidate
  archived=archive_map.get('control-plane/profiles/'+profile+'/'+normalized)
  ok=(kept.is_file() and not kept.is_symlink() and m.sha(kept)==r['sha256']) or (archived is not None and archived['sha256']==r['sha256'])
  if ok:matched+=1
  else:
   role='skills' if rel.startswith('skills-tree/') else ('historical_config_auth' if rel in ['.env','auth.json','config.yaml'] else 'control_memory_cron_or_other');unmatched[role]=unmatched.get(role,0)+1
 configs.append({'id':snap['id'],'non_db_files_byte_preserved_at_checked_paths':matched,'non_db_files_not_preserved_at_checked_paths':unmatched,'hash_mismatch_not_proof_globally_unique':True})
# Revalidate retained native sources independently of the RAM queries.
ret=json.load(open(m.PRIOR/'retained-db-integrity.json'));verified=0
for r in ret['rows']:
 if '/retry-1/cutover-checkpoints/' in r['path'] and r['path'].endswith('/state.db'):
  assert m.sha(r['path'])==r['sha256'];verified+=1
assert verified==3
message_summary=[]
for profile in ['zeus','atena','ares']:
 rows=[r for r in results if r['id'].endswith('-'+profile)];msgs=[next(t for t in r['tables'] if t['table']=='messages') for r in rows]
 assert all(t['coverage_proven'] and t['full_row_absent_from_retained_union']==0 for t in msgs)
 message_summary.append({'profile':profile,'snapshots':3,'all_message_rows_identical_in_retained_union':True,'per_snapshot_message_counts':[t['rows'] for t in msgs],'missing_message_rows':0,'historical_technical_state_or_versions_absent':True})
v=os.statvfs('/')
result={'status':'review_completed_no_deletions_blocked_on_historical_state_decision','request_message_id':m.REQUEST,'thread_id':'1569928464033783862','authority_native_verified':True,'review_scope':'12 exact profile snapshot directories across preparation/activation/recovery on21Oct; not a whole-backup-root disposal','snapshot_count':12,'regular_files':inv['regular_files'],'occupied_unique_allocated_bytes':inv['unique_allocated_bytes'],'validated_zero_historical_loss_reclaim_bytes':0,'observed_reclaim_bytes':0,'deletions':0,'messages':message_summary,'root_history':'Default/root state excluded from latest production bundle; its latest historical recovery copy covers all42messages/67sessions and is separately protected','checksum_coupled_snapshot_count':sum(bool(r['checksum_coupled_files']) for r in inv['snapshots']),'checksum_coupled_deletions_eligible_without_retirement_override':0,'sqlite_integrity_checks':'12/12 quick_check and foreign_key_check passed on RAM clones','source_preservation':preservation,'retained_native_state_db_hashes_unchanged':verified,'retained_archive_hash_unchanged':True,'original_sqlite_connections':0,'persistent_db_staging_bytes':0,'sqlite_sources_compared':'Latest native snapshot plus retained archive union for production agents; latest historical default/root copy for root','no_pk_tables_not_declared_covered_except_exact_db_identity':True,'fts_or_no_pk_counts_not_used_to_assert_unique_message_loss':True,'non_db_payload_comparison':configs,'scope_not_extended':True,'retention_policy_changed':False,'services_restarted':False,'diagnostic_recovery':'Initial equality-of-schema gate failed on legitimate recovery-phase additive schema changes; original source hashes unchanged; comparator now caches retained coverage by candidate schema projection, rerun12/12 passed','decision':'Recommend preserving a compact verified historical-difference archive before retiring old snapshot sets; alternatively explicit owner retirement may discard old technical state/config versions, not compared production message rows. Neither action is authorized by this read-only continuation. Broader point3 remains open.','next_step':'Owner choose preservation of historical technical differences versus explicit retirement; then exact-manifest confirmation before any deletion','delivery_used_percent':100*(v.f_blocks-v.f_bfree)/(v.f_blocks-v.f_bfree+v.f_bavail),'delivery_free_bytes':v.f_bavail*v.f_frsize,'completed_at':datetime.datetime.now().astimezone().isoformat()}
m.save('review-result.json',result)
# Preserve only the small audit source, not any original database or secret payload.
(m.D/'review.py').write_bytes((m.O/'review.py').read_bytes());(m.D/'finalize.py').write_bytes(Path(__file__).read_bytes())
print(json.dumps({'review':'completed','snapshots':12,'files_unchanged':inv['regular_files'],'occupied_GiB':round(inv['unique_allocated_bytes']/1024**3,2),'eligible_zero_loss_GiB':0,'deletions':0,'production_message_rows_missing':0,'checksum_coupled_snapshots':12,'retained_sources_unchanged':True}))
