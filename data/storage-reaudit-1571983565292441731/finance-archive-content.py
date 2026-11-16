"""First non-cache content pass: exactly the financial archive/SQL candidate class."""
import pathlib,os,json,gzip,stat,subprocess,collections,datetime
OUT=pathlib.Path(__file__).parent
if (OUT/'audit-final.sha256').exists():raise SystemExit('SEALED_AUDIT: use a new observation directory')
PRIVATE=pathlib.Path('/root/.hermes/secure-backups/storage-reaudit-1571983565292441731');PREFIX='/root/mgs-agent/apps/finance-system';rows=[]
for line in gzip.open(PRIVATE/'metadata-root.jsonl.gz','rt'):
 r=json.loads(line)
 if r['k']=='file'and r['p'].startswith(PREFIX+'/')and r['c']!='postgres_clusters_pending_role'and '/node_modules/'not in r['p']and r['p'].endswith(('.tar','.tar.gz','.tgz','.tar.xz','.zip','.dump','.sql')):rows.append(r)
assert len(rows)==326
ledger=PRIVATE/'finance-archive-hashes.jsonl';assert not ledger.exists();deferred=[];success=[];independent=[];dup=[];upper=0
def stable(row):
 try:s=os.lstat(row['p']);return stat.S_ISREG(s.st_mode)and(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns)==(row['d'],row['i'],row['s'],row['t'])
 except OSError:return False
for start in range(0,len(rows),16):
 batch=rows[start:start+16];good=[r for r in batch if stable(r)];deferred.extend(r['p']for r in batch if r not in good)
 if not good:continue
 out=subprocess.check_output(['nice','-n','15','ionice','-c','2','-n','7','sha256sum','--zero','--',*[r['p']for r in good]],timeout=150)
 parsed={}
 for record in out.split(b'\0'):
  if record:parsed[os.fsdecode(record[66:])]=record[:64].decode()
 assert len(parsed)==len(good)
 with open(ledger,'a')as f:
  for r in good:
   if not stable(r):deferred.append(r['p']);continue
   rec=dict(path=r['p'],sha256=parsed[r['p']],size=r['s'],allocated=r['b'],dev=r['d'],ino=r['i'],nlink=r['n']);success.append(rec);f.write(json.dumps(rec)+'\n')
  f.flush();os.fsync(f.fileno())
 groups=collections.defaultdict(list)
 for r in success:groups[(r['size'],r['sha256'])].append(r)
 dup=[g for g in groups.values()if len(g)>1];independent=[g for g in dup if len({(r['dev'],r['ino'])for r in g})>1];upper=0
 for g in independent:
  alloc={(r['dev'],r['ino']):r['allocated']for r in g};upper+=sum(alloc.values())-min(alloc.values())
 (OUT/'finance-archive-content-progress.json').write_text(json.dumps(dict(considered=min(start+16,len(rows)),hashed=len(success),deferred=len(deferred),independent_duplicate_groups=len(independent),duplicate_allocated_upper_bound_bytes=upper,not_a_deletion_manifest=True),indent=2)+'\n')
(private_result:=PRIVATE/'finance-archive-duplicate-groups.json').write_text(json.dumps(dict(groups=independent),indent=2)+'\n')
result=dict(status='content_pass_complete',declared_candidate_files=326,files_SHA256_verified=len(success),metadata_drift_deferred=deferred,identical_content_groups=len(dup),groups_with_independent_inodes=len(independent),duplicate_allocated_upper_bound_bytes=upper,duplicate_upper_bound_GiB=round(upper/1024**3,3),potential_not_certified_reclaim=True,canonical_provider_not_selected=True,current_consumers_and_recovery_not_yet_certified=True,new_deletion_targets_certified=0,source_files_deleted=0,raw_payloads_copied=False,large_new_backups_created=False,private_hash_ledger=str(ledger),private_group_ledger=str(private_result),at=datetime.datetime.now().astimezone().isoformat())
(OUT/'finance-archive-content-review.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
