"""Surgical infra inventory/audit registration for this completed maintenance."""
import fcntl
import hashlib
import json
import os
from datetime import datetime,timezone
from pathlib import Path
B=Path('/root/mgs-agent');W=B/'work/t_7ab9e9ba';dep=json.loads((W/'deployment-receipt.json').read_text());tests=json.loads((W/'pytest-installed.json').read_text());stamp=datetime.now(timezone.utc).isoformat();key='shein-static-images-central-t_7ab9e9ba'
paths=[B/'scripts/ares_campaign_v3'/n for n in dep['changed_modules']]+[B/'tests/test_shein_image_media.py',Path('/root/.hermes/profiles/zeus/skills/growth/meta-ads-api-operations/references/shein-static-image-prestage.md')]
files=[{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'size_bytes':p.stat().st_size} for p in paths]
entry={'id':key,'agent':'zeus','type':'backward-compatible-shein-static-image-media-support','status':'installed_local_validation_passed_live_campaign_acceptance_pending','updated_at':stamp,'task_id':'t_7ab9e9ba','request_id':'shein-1565747351543480374','origin_thread_id':'1558134703565967394','operation':'SHEIN-US-DIRECT','authority':['SHEIN-US-DIRECT.json#/grouped_manager_media_policy','context/routes.md#delegação-histórica-de-recovery-ares--zeus'],'files':files,'tests_passed':tests['passed'],'baseline_exclusions':tests['exclusion'],'subtests_passed':295,'real_images_byte_verified':16,'source_live_campaign_id':'120250750964580629','real_input_contract_replay':'passed with isolated synthetic media registry; not live readiness','live_adimages_read':'HTTP200 in unchanged Ares scope','meta_writes':0,'drive_writes':0,'inventory_reservations':0,'credentials_guards_budget_sla_changed':False,'deployment_receipt':str(W/'deployment-receipt.json'),'rollback_package':dep['rollback_package'],'validation_receipt':str(W/'pytest-installed.json'),'next_owner':'ares','next_task':'t_8f7a90a8','pending':['real account-scoped pre-stage and registry hash readback','real campaign dry-run/plan','all-image Meta rendered previews and semantic/inventory QA','same-request central execution and final ACTIVE readback under original timing policy']}
report_path=W/'report-infra-readback.json'
if report_path.exists():entry['report_infra']=json.loads(report_path.read_text())
p=B/'data/infra-inventory.json'
with p.with_suffix('.json.lock').open('a+') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX)
    original=p.read_bytes();(W/'infra-inventory-before.json').write_bytes(original) if not (W/'infra-inventory-before.json').exists() else None
    d=json.loads(original)
    rows=d.setdefault('runtime_artifacts',[]);old=[x for x in rows if x.get('id')==key]
    if old:rows[rows.index(old[0])]=entry
    else:rows.append(entry)
    indexed={x['path']:x for x in d.setdefault('scripts',[]) if isinstance(x,dict) and 'path' in x}
    for f in files:
        if not f['path'].startswith(str(B/'scripts')+'/'):continue
        target=Path(f['path']);row=indexed.get(str(target))
        fresh={'path':str(target),'size_bytes':target.stat().st_size,'modified_at':datetime.fromtimestamp(target.stat().st_mtime,timezone.utc).isoformat()}
        if row:row.update(fresh)
        else:d['scripts'].append(fresh)
    d['_meta']['updated_at']=stamp
    assert p.read_bytes()==original,'concurrent inventory change'
    temp=p.with_suffix('.t_7ab9e9ba.tmp');temp.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n');os.chmod(temp,0o600);os.replace(temp,p)
    saved=json.loads(p.read_text());match=[x for x in saved['runtime_artifacts'] if x.get('id')==key];assert len(match)==1 and match[0]==entry
marker=W/'audit-recorded.json'
if not marker.exists():
    event={'timestamp':stamp,'agent':'zeus','action':'shein_static_image_central_maintenance','task_id':'t_7ab9e9ba','request_id':entry['request_id'],'origin_thread_id':entry['origin_thread_id'],'scope':'local central maintenance only; original campaign remains Ares-owned','authority':entry['authority'],'result':entry['status'],'evidence':str(W/'pytest-installed.json'),'tests_passed':tests['passed'],'baseline_exclusions':3,'meta_writes':0,'drive_writes':0,'reservations':0,'rollback':dep['rollback_package']}
    with (B/'logs/events-audit.jsonl').open('a') as handle:
        fcntl.flock(handle,fcntl.LOCK_EX);handle.write(json.dumps(event,ensure_ascii=False)+'\n');handle.flush();os.fsync(handle.fileno())
    marker.write_text(json.dumps(event,indent=2)+'\n')
print(json.dumps({'inventory_entry':key,'files':len(files),'readback_equal':True,'audit_recorded':True,'report_infra_registered':report_path.exists()}))
