"""Canonical role ledger, still a live observation and not a deletion approval."""
import pathlib,json,gzip,collections,os
OUT=pathlib.Path(__file__).parent;PRIVATE=pathlib.Path('/root/.hermes/secure-backups/storage-reaudit-1571983565292441731');DEPARTED='/root/mgs-agent/tmp/mgs-dr-backup-uipjbqf9';assert not os.path.exists(DEPARTED)
def under(p,r):return p==r or p.startswith(r+'/')
def role(r):
 p=r['p'];base=r['c']
 if under(p,DEPARTED):return 'observed_native_backup_transient_now_completed'
 if under(p,'/root/mgs-agent/backups'):return 'application_and_infrastructure_backup_copies_pending_proof'
 if under(p,'/root/mgs-agent/tmp'):return 'local_execution_temporaries_pending_proof'
 prefix='/root/.hermes/profiles/'
 if p.startswith(prefix):
  parts=p[len(prefix):].split('/');tail=parts[1:];first=tail[0]if tail else''
  if first in {'workspace','workspaces','work','codex-pilots'}:return 'agent_working_and_test_material_pending_proof'
  if first in {'reports','artifacts'}:return 'agent_evidence_and_media_pending_lineage'
  if first=='state-snapshots':return 'agent_historical_state_snapshots_pending_recovery_proof'
  if first.startswith('state.db')or first.startswith('state_')or first in {'sessions','checkpoints'}:return 'agent_live_history_sessions_and_checkpoints'
  if first in {'browser-binaries','stt-runtime','mcp','lsp'}:return 'installed_agent_tools_and_binaries'
 return base
inodes={};counts=collections.Counter();departed=collections.Counter()
for fs in json.load(open(OUT/'metadata-summary.json'))['filesystems']:
 for line in gzip.open(fs['ledger'],'rt'):
  r=json.loads(line);cat=role(r);counts[cat]+=1;key=(r['d'],r['i'])
  if cat=='observed_native_backup_transient_now_completed':departed[r['k']]+=1
  if key not in inodes:inodes[key]=[r['b'],cat]
  elif inodes[key][1]!=cat:inodes[key][1]='shared_hardlinks_between_classes'
sizes=collections.Counter()
for alloc,cat in inodes.values():sizes[cat]+=alloc
old=json.load(open(OUT/'metadata-summary.json'));assert sum(sizes.values())==sum(f['unique_allocated_bytes']for f in old['filesystems'])
result=dict(status='role_ledger_verified',all_values_occupied_not_disposable_bytes=True,snapshot_allocation_total_bytes=sum(sizes.values()),snapshot_categories=[dict(category=c,unique_allocated_bytes=b,GiB=round(b/1024**3,3),nodes=counts[c])for c,b in sizes.most_common()],confirmed_native_transient_departed=dict(path=DEPARTED,counts=dict(departed),allocated_bytes=sizes['observed_native_backup_transient_now_completed'],producer_proof='transient-backup-reconciliation.json',removed_by_this_audit=False),scan_allocation_minus_confirmed_departed_bytes=sum(sizes.values())-sizes['observed_native_backup_transient_now_completed'],known_current_variation_still_possible=True,caches_cleanup_paused=True,eligible_new_delete_targets=0,source_metadata_preserved=True)
(OUT/'category-role-ledger.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:round(v/1024**3,3)for k,v in sizes.most_common()}));print('CLASS_PARTITION_ASSERT_PASS')
