#!/usr/bin/env python3
"""Scoped infra inventory merge: preserve all sibling records under lock/CAS."""
import fcntl,hashlib,json,os
from datetime import datetime,timezone
from pathlib import Path
R=Path('/root/mgs-agent');H=Path(__file__).parent;p=R/'data/infra-inventory.json'
changes=json.loads((H/'changes.json').read_text())|json.loads((H/'supplement-changes.json').read_text())
now=datetime.now(timezone.utc).isoformat();oldrows=[]
with p.with_suffix('.json.lock').open('a+') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX);raw=p.read_bytes();data=json.loads(raw)
 for filename in changes:
  path=R/filename;key='scripts' if filename.startswith('scripts/') else 'data_files'
  rows=data[key];prior=next((row for row in rows if row.get('path')==str(path)),None)
  if prior:oldrows.append({'kind':key,'row':prior.copy()})
  row={'path':str(path),'size_bytes':path.stat().st_size,'modified_at':datetime.fromtimestamp(path.stat().st_mtime,timezone.utc).isoformat(),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'maintenance_task':'t_247b861d'}
  if prior:prior.update(row)
  else:rows.append(row)
 artifact={'id':'ares-eggbev01-ana-m6-t_247b861d','agent':'ares','type':'account_scoped_meta_app_binding','status':'INSTALLED_READBACK_VALIDATED_NO_CAMPAIGN_PREPARATION','updated_at':now,'account_id':'1034081997659047','app_id':'953171080682697','token_identity':'Ana Cunha','marketing_api_access_tier':'development_access','canonical_source':'data/ares/meta-ads/accounts/1034081997659047.json','evidence':'data/ares/meta-ads/audit/maintenance/t_247b861d/post-cutover-readback.json','install_receipt':'data/ares/meta-ads/audit/maintenance/t_247b861d/install-receipt.json','tests':'data/ares/meta-ads/audit/maintenance/t_247b861d/installed-tests.json','meta_writes':0,'source_campaign_unchanged':True,'historical_coordination':'SUSPENDED_BY_OPERATOR; never campaign COMPLETE','other_accounts_unchanged':True}
 assert not any(v.get('id')==artifact['id'] for v in data['runtime_artifacts']);data['runtime_artifacts'].append(artifact)
 assert p.read_bytes()==raw,'infra inventory concurrent modification; retry merge from current state'
 tmp=p.with_suffix('.t_247b861d.new');tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n');tmp.chmod(p.stat().st_mode&0o777);os.replace(tmp,p)
 live=json.loads(p.read_text());assert next(v for v in live['runtime_artifacts'] if v.get('id')==artifact['id'])==artifact
 (H/'inventory-receipt.json').write_text(json.dumps({'inventory':str(p.relative_to(R)),'before_sha256':hashlib.sha256(raw).hexdigest(),'after_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'scoped_merge_verified':True,'updated_exact_paths':list(changes),'prior_exact_rows':oldrows,'runtime_artifact_id':artifact['id']},ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'inventory_scoped_merge_verified':True,'runtime_artifact_id':artifact['id'],'paths':len(changes)}))
