import pathlib,json,gzip,os,subprocess,datetime,collections
OUT=pathlib.Path(__file__).parent
existing=OUT/'review-result.json'
if existing.exists() and json.loads(existing.read_text()).get('report_infra',{}).get('verified'):
 raise SystemExit('Refusing to replace a sealed review receipt; read the existing result instead.')
ID='1571239570069131275'
def sha(p):return subprocess.check_output(['sha256sum','--',str(p)],text=True).split()[0]
metadata=json.load(open(OUT/'metadata-result.json'));before=json.load(open(OUT/'protected-before.json'));pres=json.load(open(OUT/'preservation-result.json'));compat=json.load(open(OUT/'native-import-compatibility.json'));deps=json.load(open(OUT/'dependencies.json'))
assert len(metadata['roots'])==2 and not metadata['scan_errors']
assert len(pres['replays'])==2 and len(compat['results'])==2
assert all(r['returncode']==0 and r['probe']['imports_ok'] and r['probe']['adapter_call_signature_accepted'] for r in compat['results'])
assert not deps['process_references'] and not deps['source_errors']
assert sha(pres['archive'])==pres['archive_sha256']
stability=[]
for row in metadata['roots']:
 root=pathlib.Path(row['root']);checked=0;differences=[]
 with gzip.open(row['metadata_ledger'],'rt')as f:
  for line in f:
   d=json.loads(line);p=root/d['path'];st=p.lstat();current={'mode':st.st_mode,'size':st.st_size,'mtime_ns':st.st_mtime_ns,'ctime_ns':st.st_ctime_ns,'allocated':st.st_blocks*512,'dev':st.st_dev,'ino':st.st_ino,'nlink':st.st_nlink}
   if any(current[k]!=d[k]for k in current):differences.append(d['path'])
   if d['kind']=='link' and os.readlink(p)!=d['target']:differences.append(d['path'])
   checked+=1
 assert not differences,{'root':str(root),'differences':differences[:10]}
 stability.append({'root':str(root),'metadata_entries_unchanged':checked,'counts':row['counts'],'inode_unique_occupied_bytes':row['inode_unique_occupied_bytes'],'conditional_reclaim_bytes_not_eligible':row['exclusive_reclaim_if_all_other_gates_pass'],'base_commit':row['head']})
for row in before['files']:
 assert sha(row['path'])==row['sha256'] and pathlib.Path(row['path']).stat().st_size==row['size'],row['path']
for p,d in before['launchers'].items():
 path=pathlib.Path(p)
 if d['symlink']:assert path.is_symlink()and os.readlink(path)==d['target'],p
 if d['sha256']:assert sha(path)==d['sha256'],p
for profile,d in before['services'].items():
 pid=subprocess.check_output(['systemctl','show',profile+'-gateway.service','-p','MainPID','--value'],text=True).strip()
 assert int(pid)==d['pid'];assert subprocess.run(['systemctl','is-active','--quiet',profile+'-gateway.service']).returncode==0
live=pathlib.Path('/root/.hermes/profiles/zeus/skills/ops/vps-maintenance-and-backup-governance/references/backup-retention-scope-and-redundancy.md');mirror=pathlib.Path('/root/mgs-agent/profiles/zeus-skills/ops/vps-maintenance-and-backup-governance/references/backup-retention-scope-and-redundancy.md');assert sha(live)==sha(mirror)
fs=os.statvfs('/');disk: dict[str, int | float]={'available_bytes':fs.f_bavail*fs.f_frsize,'used_bytes':(fs.f_blocks-fs.f_bfree)*fs.f_frsize};disk['used_percent']=round(100*disk['used_bytes']/(disk['used_bytes']+disk['available_bytes']),2)
result={'status':'review_completed_preserved_dependencies_pending','authority_message_id':ID,'thread_id':'1569928464033783862','review_scope':['46904a3b','ad2d4822'],'roots':stability,'protected_file_hashes_unchanged':len(before['files']),'all_hermes_launchers_unchanged':len(before['launchers']),'gateway_pids_unchanged':{k:v['pid']for k,v in before['services'].items()},'services_active':3,'deletions':0,'source_runtime_mutations':0,'campaign_meta_pc1_actions':0,'cron_or_retention_changes':0,'new_eligible_reclaim_bytes':0,'occupied_and_hypothetical_reclaim_are_not_disposal_authority':True,'preservation':pres,'native_import_probe_status':'2/2 real imports and call binding passed; no desktop handler or activation called','blocked_adapter_early_return_tests':'2/2 passed with subprocess tripwire','remaining_gates':{'46904a3b':['Two technical helper literals still select the old Python/runtime.','49-item DigitalTrust request remains blocked and must not be resumed/cancelled by cleanup.','Any helper migration requires bounded staging/validation separate from business execution.','Old virtualenv payload/local overrides have not been fully audited/rebuilt.'],'ad2d4822':['Configured legacy executable symlink still points into this root.','Dirty linked Git worktree must use native retirement with exact admin scope, not raw tree removal.','Old virtualenv payload/local overrides have not been fully audited/rebuilt.']},'preserved_test_state':'12 MagicMock historical files reproduced byte-for-byte; original SQLite files not opened; no logical database restore claimed','no_deletion_manifest_prepared':True,'separate_broad_cleanup_not_closed':True,'next_recommended_decision':'Authorize only technical helper migration preparation/cutover with no Meta/PC1 calls or cron/campaign/batch resumption; then freeze a new exact runtime/legacy-launcher lot if all remaining gates pass. No deletion is authorized by this review.','skill_updated':str(live),'skill_mirror':str(mirror),'skill_live_mirror_sha256':sha(live),'diagnostic_recoveries':['Disabled generic Hermes skill read directly without enabling it.','Legacy interpreter assumptions failed before imports; live MainPID and read-only native project_python resolver selected managed generation; both actual import probes passed.','Tool file-copy adapter refused formatted display then returned read dedup; copied only authored source files byte-for-byte and verified external SHA-256 equality.'],'private_preservation_root':str(pathlib.Path(pres['archive']).parent),'analysis_created_scratch_roots':[pres['scratch'],'/root/.hermes/profiles/zeus/cache/scratch/conditional-native-import-'+ID],'disk_observed':disk,'observed_at':datetime.datetime.now().astimezone().isoformat(),'report_infra':{'status':'pending'}}
(OUT/'review-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':result['status'],'roots':stability,'protected_files':len(before['files']),'services_active':3,'pids_preserved':True,'source_patch_files_replayed':sum(x['modified_source_files_replayed']for x in pres['replays']),'overlay_files_replayed':sum(x['overlay_files_replayed']for x in pres['replays']),'deletions':0,'eligible_reclaim_bytes':0,'disk':disk},ensure_ascii=False))
