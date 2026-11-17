"""Upsert only this audit's infrastructure row; preserve concurrent inventory data."""
import datetime,fcntl,json,os,pathlib,stat,tempfile
R=pathlib.Path('/root/mgs-agent');O=pathlib.Path(__file__).parent
if(O/'retirement-final.json').exists():raise SystemExit('LOT_COMPLETED_DO_NOT_REOPEN_PROPOSAL')
inv=R/'data/infra-inventory.json';result=json.loads((O/'review-result.json').read_text());receipt=O/'report-infra.json';report=json.loads(receipt.read_text())if receipt.exists()else{'status':'pending_post_and_exact_readback'};key='storage-rollback-dumps-1572270579850153987';scratch=pathlib.Path('/root/.hermes/profiles/zeus/cache/scratch');assert pathlib.Path(os.environ['TMPDIR']).resolve()==scratch.resolve()
with (O/'inventory-update.lock').open('a')as lock:
 fcntl.flock(lock,fcntl.LOCK_EX);raw=inv.read_bytes();s=inv.stat();d=json.loads(raw);seq=d['runtime_artifacts'];matches=[x for x in seq if isinstance(x,dict)and x.get('id')==key];assert len(matches)<=1
 row=dict(id=key,agent='zeus',type='readonly_historical_dump_review_and_exact29_remote_mirrored_local_file_proposal',status='awaiting_new_exact_critical_confirmation',thread_id='1569928464033783862',authority_message_id='1572270579850153987',reviewed_count=90,candidate_files=29,preserved_pending_proof=61,source_files_deleted=0,directories_to_delete=0,manifest_sha256=result['manifest_sha256'],gate_sha256=result['gate_sha256'],gross_reclaim_bytes=result['gross_reclaim_bytes'],net_direct_reclaim_estimate_bytes=result['net_direct_reclaim_estimate_bytes'],retained_unique_payloads=294,retained_original_cohort=293,retained_parent_directories=29,remote_originals_verified=29,additional_fallback_remote_verified=True,real_retained_only_RAM_file_recoveries=29,gate_tests=29,gate_preflight='PASS',learning=result['learning'],evidence=str((O/'review-result.json').relative_to(R)),source_census_path='/root/.hermes/secure-backups/storage-rollback-dumps-1572270579850153987/source-census-frozen-v2.json.gz',private_recovery_ledger='/root/.hermes/secure-backups/storage-rollback-dumps-1572270579850153987/selected-lineage.json.gz',mandatory_retained_recovery_dependencies=[x['remote_path']for x in json.loads((O/'manifest.json').read_text())['remote_recovery']],report_infra=report,new_critical_confirmation_pending=True,existing_approvals_applicable=False,next_step=result['next_step'],updated_at=datetime.datetime.now().astimezone().isoformat())
 if matches:seq[seq.index(matches[0])]=row
 else:seq.append(row)
 d['_meta']['updated_at']=row['updated_at'];fd,name=tempfile.mkstemp(prefix='storage-rollback-inventory-',suffix='.json',dir=scratch)
 with os.fdopen(fd,'w')as f:os.fchown(f.fileno(),s.st_uid,s.st_gid);os.fchmod(f.fileno(),stat.S_IMODE(s.st_mode));json.dump(d,f,indent=2,ensure_ascii=False);f.write('\n');f.flush();os.fsync(f.fileno())
 assert inv.read_bytes()==raw,'CONCURRENT_INVENTORY_WRITE_PRESERVED_ABORT_BEFORE_REPLACE';os.replace(name,inv)
readback=json.loads(inv.read_text());found=[x for x in readback['runtime_artifacts']if isinstance(x,dict)and x.get('id')==key];assert found==[row]
if not(O/'governance-audit-written.json').exists():
 event=dict(at=row['updated_at'],agent='zeus',event='storage_rollback_dump_readonly_review_exact29_ready',request_message_id='1572270579850153987',thread_id='1569928464033783862',manifest_sha256=row['manifest_sha256'],reviewed=90,candidate_files=29,preserved=61,deleted=0)
 with(R/'logs/events-audit.jsonl').open('a')as f:f.write(json.dumps(event)+'\n');f.flush();os.fsync(f.fileno())
 (O/'governance-audit-written.json').write_text(json.dumps(event)+'\n')
print(json.dumps({'inventory_exact_single_row_verified':True,'report_infra':report,'source_files_deleted':0}))
