"""Inventory, audit and exact readback; no campaign/media records are edited."""
import fcntl,hashlib,json,os,sys,tempfile
from datetime import datetime,timezone
from pathlib import Path
B=Path('/root/mgs-agent');W=B/'work/t_8426333c'
sys.path.insert(0,str(B/'scripts'))
from ares_campaign_v3.shein_single_clone import atomic_json

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
base=json.loads((W/'baseline.json').read_text());dep=json.loads((W/'deployment-receipt.json').read_text());reg=json.loads((W/'regression-installed.json').read_text())
assert reg['exit_code']==0 and reg['passed']==583 and reg['subtests_passed']==484 and reg['files']==46 and not reg['failed'] and not reg['skipped'] and not reg['exclusions'] and not reg['module_origin_mismatch'] and not reg['external_network_attempts_blocked']
files={**dep['changed_runtime_files'],**dep['tests']}
assert all(digest(Path(p))==h for p,h in files.items())
assert all(digest(B/'scripts/ares_campaign_v3'/n)==h for n,h in base['package'].items() if n!='preview_renderer.py')
checks={p:{'sha256':h,'unchanged':digest(Path(p))==h} for p,h in base['protected'].items()}
assert all(v['unchanged'] for v in checks.values())
skill=Path('/root/.hermes/profiles/ares/skills/growth/meta-campaign-engine-v3/references/architecture-and-runtime.md');mirror=B/'profiles/ares-skills/growth/meta-campaign-engine-v3/references/architecture-and-runtime.md'
assert skill.read_bytes()==mirror.read_bytes()
now=datetime.now(timezone.utc).isoformat()
entry={'id':'chromium-preview-readiness-t_8426333c','agent':'ares','task_id':'t_8426333c','type':'central-renderer-startup-hardening','status':'installed_and_regression_verified','updated_at':now,
'files':[{'path':p,'sha256':h,'size_bytes':Path(p).stat().st_size} for p,h in files.items()],
'backup':dep['backup'],'backup_sha256':dep['backup_sha256'],'deployment':str(W/'deployment-receipt.json'),'regression':reg,
'confirmed_cause':'DevToolsActivePort exists before complete write; original empty-file IndexError reproduced deterministically without network.',
'readiness_contract':'Complete valid port/browser path plus matching live loopback /json/version, bounded monotonic startup deadline and child liveness before attach.',
'cleanup':'Owned process group only, wait/reap then temporary profile cleanup; installed runtime preserved; exercised locally with real Chromium and dead child.',
'learning':{'profile':'ares','path':str(skill),'sha256':digest(skill),'source_mirror_equal':True,'readback_and_tests':'PASS','other_agent_skills_changed':False},
'protected_files_unchanged':len(checks),'other_package_modules_unchanged':True,'scope':'Launcher only; URL/media/activation gates and timeout policy unchanged; no campaign changes.',
'meta_writes':0,'drive_writes':0,'credentials_changed':False,'gateway_restart':False,'campaign_canary':False,
'evidence':str(W/'report.md'),'recovered_local_publication_guard':'Candidate .py was included by own package CAS glob; installed original unchanged. Reconciled candidate hash and reused same unpublished file as .tmp before atomic replace.',
'rollback_contract':'Restore only backed-up preview_renderer.py after current-state reconciliation under maintenance/account/request locks and CAS. Do not restore old operational state or delete installed runtime.'}
rp=W/'report-infra-readback.json'
if rp.exists():entry['report_infra']=json.loads(rp.read_text())
p=B/'data/infra-inventory.json'
with p.with_suffix('.maintenance.lock').open('a+') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX)
    before=p.read_bytes();data=json.loads(before);rows=data.setdefault('runtime_artifacts',[]);found=[i for i,r in enumerate(rows) if isinstance(r,dict) and r.get('id')==entry['id']];assert len(found)<=1
    backup=W/'backup/infra-inventory-before.json'
    if not backup.exists():backup.write_bytes(before)
    if found:rows[found[0]]=entry
    else:rows.append(entry)
    assert p.read_bytes()==before
    atomic_json(p,data)
assert [r for r in json.loads(p.read_text())['runtime_artifacts'] if isinstance(r,dict) and r.get('id')==entry['id']]==[entry]
(W/'inventory-readback.json').write_text(json.dumps(entry,ensure_ascii=False,indent=2)+'\n')
(W/'preserved-state-readback.json').write_text(json.dumps({'at':now,'paths':checks,'operational_edits':0},indent=2)+'\n')
audit={'timestamp':now,'agent':'ares','task_id':'t_8426333c','action':'chromium_readiness_report_verified' if rp.exists() else 'chromium_readiness_installed','inventory_id':entry['id'],'deployment':dep['changed_runtime_files'],'passed':reg['passed'],'subtests_passed':reg['subtests_passed'],'protected_files_unchanged':len(checks),'meta_writes':0,'drive_writes':0,'gateway_restart':False,'learning':entry['learning']}
if rp.exists():audit['report_infra_message_id']=entry['report_infra']['message_id']
fd=os.open(B/'logs/events-audit.jsonl',os.O_WRONLY|os.O_APPEND)
try:
    fcntl.flock(fd,fcntl.LOCK_EX);os.write(fd,(json.dumps(audit,ensure_ascii=False)+'\n').encode());os.fsync(fd)
finally:os.close(fd)
print(json.dumps({'inventory_id':entry['id'],'exact_readback':True,'files_verified':len(files),'protected_files_unchanged':len(checks),'report_infra_verified':rp.exists(),'passed':reg['passed'],'subtests_passed':reg['subtests_passed']}))
