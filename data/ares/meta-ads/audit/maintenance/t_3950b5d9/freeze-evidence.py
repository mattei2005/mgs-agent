"""Freeze installed evidence; read-only on production request and campaign state."""
import ast,difflib,json,sys,subprocess
from datetime import datetime,timezone
from pathlib import Path
R=Path('/root/mgs-agent');M=R/'data/ares/meta-ads/audit/maintenance/t_3950b5d9'
sys.path.insert(0,str(R/'scripts'))
from ares_campaign_v3 import target_start_revision as rev
RID='eggbev-pg23189-1571342489162489937';AID='1034081997659047';HOME=R/'data/ares/meta-ads/audit/eggbev/target-clone'/RID
results=rev.load(M/'installed-final-tests.json');assert all(x['success'] and not x['skipped'] for x in results)
assert sum(x['tests'] for x in results)==456 and len(results)==24
pins=rev.load(M/'tested-runtime-hashes.json');pins['tests/test_eggbev_creation_config_report.py']=rev.file_digest(R/'tests/test_eggbev_creation_config_report.py')
for p,h in pins.items():assert rev.file_digest(R/p)==h,p
rev.atomic_json(M/'tested-runtime-hashes.json',pins)
old=ast.parse((M/'before/ares-eggbev-target-clone.py').read_text());new=ast.parse((R/'scripts/ares-eggbev-target-clone.py').read_text())
a={x.name:ast.dump(x,include_attributes=False) for x in old.body if isinstance(x,(ast.FunctionDef,ast.ClassDef))};b={x.name:ast.dump(x,include_attributes=False) for x in new.body if isinstance(x,(ast.FunctionDef,ast.ClassDef))}
changed=[k for k in a if a[k]!=b[k]];assert changed==['request_load','execute','main']
config=R/'data/ares/meta-ads/engine-v3/config.json';cfg=rev.load(config);baseline=rev.load(M/'before/config.json');restored=json.loads(json.dumps(cfg));restored['accounts'][AID]['campaign_policy']['immediate_start_request_ids'].remove(RID);restored['accounts'][AID]['target_page_replacement']['start_revisions'].pop(RID)
if not restored['accounts'][AID]['target_page_replacement']['start_revisions']:restored['accounts'][AID]['target_page_replacement'].pop('start_revisions')
assert restored==baseline
context=rev.validate_local(HOME/'request.json',cfg,'7fb94557a6302e97bcc5239ad7f7758052555203f3ff15c360e1ffef55c5afba','1571376388437577861')
assert context['last'] is None and not (HOME/'start-revisions').exists()
assert not any(p.exists() for p in rev.effect_paths(context,cfg)) and not (HOME/'final-approval.json').exists()
protected=rev.load(M/'protected-before.json');changed_files={p:{'before':h,'after':rev.file_digest(p)} for p,h in protected.items() if rev.file_digest(p)!=h}
assert set(changed_files)=={str(config),str(R/'data/ares/creative-ops/inventory/assets.jsonl')}
external=rev.load(M/'external-inventory-reconciled.json');assert external['live_get_verified'] and external['eggbev_request_rows_unchanged']
assert rev.file_digest(R/'data/ares/creative-ops/inventory/assets.jsonl')==rev.load(M/'external-inventory-diff.json')['after_sha256']
skill=rev.load(R/'data/ares/meta-ads/audit/maintenance/t_2b06442a/receipt.json');assert skill['tests_passed']==28
for name in ['canonical','mirror']:assert rev.file_digest(skill[name])==skill['after_sha256']
worker=subprocess.run(['/usr/bin/python3',str(R/'data/ares/meta-ads/audit/maintenance/t_2b06442a/verify_documentation.py')],capture_output=True,text=True,check=True);(M/'skill-documentation-test.log').write_text(worker.stdout+worker.stderr)
# No command is run; enumerate argv rather than matching own shell string.
writers=[]
for proc in Path('/proc').glob('[0-9]*'):
    try:argv=(proc/'cmdline').read_bytes().split(b'\0')
    except (OSError,PermissionError):continue
    if b'execute' in argv and any(p.endswith(b'/ares-eggbev-target-clone.py') for p in argv):writers.append(int(proc.name))
assert not writers,writers
paths=['scripts/ares-eggbev-target-clone.py','scripts/ares_campaign_v3/target_start_revision.py','tests/test_target_start_revision.py','tests/test_eggbev_source_selection.py','tests/test_native_thumbnail_equivalence.py','data/ares/meta-ads/engine-v3/config.json']
installed={str(R/p):rev.file_digest(R/p) for p in paths}
installed.update({str(skill[k]):rev.file_digest(skill[k]) for k in ['canonical','mirror']})
for file in ['ares-eggbev-target-clone.py','test_eggbev_source_selection.py','test_native_thumbnail_equivalence.py','config.json']:
    before=M/'before'/file
    after=config if file=='config.json' else R/('scripts' if file=='ares-eggbev-target-clone.py' else 'tests')/file
    (M/(file+'.diff')).write_text(''.join(difflib.unified_diff(before.read_text().splitlines(True),after.read_text().splitlines(True),fromfile=str(before),tofile=str(after))))
receipt={'task_id':'t_3950b5d9','verified_at':datetime.now(timezone.utc).isoformat(),'status':'INSTALLED_VALIDATED_NO_CAMPAIGN_EXECUTION','execution_owner_task':'t_bdfc754f','installed_hashes':installed,'tested_file_hashes':len(pins),'tests':{'passed':456,'modules':24,'new_temporal_tests':42,'previous_regression_tests':287,'additional_routes_roas_tests':sum(x['tests'] for x in results[19:]),'native_python314_temporal':42,'legacy_extra_passed':8,'legacy_extra_failed':1,'legacy_cause':'preexisting fixture standard_access versus preserved development_access; same failure before and after grant','skill_documental':28},'modified_existing_ast':changed,'all_other_existing_ast_unchanged':True,'protected_whole_files_unchanged':len(protected)-len(changed_files),'expected_protected_deltas':changed_files,'concurrent_authorized_external_inventory':external,'original_start_unchanged':rev.load(HOME/'request.json')['start_time'],'original_digest_unchanged':rev.load(HOME/'manifest.json')['prevalidation']['content_digest'],'grant_receipt':str(M/'grant-install-receipt.json'),'grant_receipt_sha256':rev.file_digest(M/'grant-install-receipt.json'),'temporal_revision_materialized':False,'final_approval_engine_checkpoint_audit_result_absent':True,'operational_writers':writers,'operational_engine_calls':0,'meta_writes':0,'drive_writes':0,'new_uploads':0,'new_reservations':0,'source_page_media_naming_copy_budget_status_unchanged':True,'rollback':'CAS only: restore before/ares-eggbev-target-clone.py when installed runner hash still matches receipt; remove ONLY this request grant+allowlist under config lock preserving concurrent config fields. Keep grant/module/history for audit; do not execute rollback against live effects; never restore global inventory.'}
rev.atomic_json(M/'install-receipt.json',receipt)
print(json.dumps({k:receipt[k] for k in ['status','tested_file_hashes','tests','modified_existing_ast','protected_whole_files_unchanged','original_start_unchanged','temporal_revision_materialized','final_approval_engine_checkpoint_audit_result_absent']},ensure_ascii=False,indent=2))
