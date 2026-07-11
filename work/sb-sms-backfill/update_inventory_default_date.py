#!/usr/bin/env python3
import json,os,hashlib
from datetime import datetime,timezone
inv='/root/mgs-agent/data/infra-inventory.json';log='/root/mgs-agent/logs/events-audit.jsonl';root='/tmp/mgs-quiz-carro-audit/mgs-quiz-carro'
def meta(rel):
 b=open(os.path.join(root,rel),'rb').read();return {'path':rel,'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}
d=json.load(open(inv));m=[x for x in d.get('runtime_artifacts',[]) if x.get('plugin')=='mgs-quiz-carro' and x.get('site')=='creditoparaveiculo.com']
if len(m)!=1:raise SystemExit(f'expected one artifact, got {len(m)}')
a=m[0];a.update({'id':'creditoparaveiculo-mgs-quiz-carro-1.7.2-20260710','version':'1.7.2','package_sha256':'d8eb20f40931a6d82a3ac98f73d0b90d9c7d51cb045c9f524ebb210413543ba8','backup_path':'/home/runcloud2/backups/creditoparaveiculo/mgs-quiz-carro-1.7.1-20260711T013155Z','files':[meta('mgs-quiz-carro.php'),meta('includes/class-mgs-quiz-admin.php'),meta('includes/class-mgs-quiz-activator.php')],'report_default_dates':{'from':'previous day','to':'previous day','timezone':'WordPress site timezone','explicit_query_dates_preserved':True},'validation':'PHP lint 11/11; default from/to both 2026-07-09 in WP timezone at validation time; explicit date/ROI/revenue regressions pass; four quiz routes HTTP 200','updated_at':datetime.now(timezone.utc).isoformat()});d['updated_at']=datetime.now(timezone.utc).isoformat();tmp=inv+'.tmp';json.dump(d,open(tmp,'w'),ensure_ascii=False,indent=2);open(tmp,'a').write('\n');json.load(open(tmp));os.replace(tmp,inv)
e={'timestamp':datetime.now(timezone.utc).isoformat(),'event':'mgs_quiz_report_default_yesterday_deployed','actor':'zeus','site':'creditoparaveiculo.com','plugin':'mgs-quiz-carro','version':'1.7.2','behavior':'from/to default to previous day in WordPress timezone when absent; explicit dates preserved','validated_default':'2026-07-09','package_sha256':a['package_sha256'],'backup_path':a['backup_path']}
with open(log,'a') as f:f.write(json.dumps(e,ensure_ascii=False)+'\n')
print('DEFAULT_DATE_INVENTORY_AUDIT_OK',a['version'],a['files'][1]['sha256'][:12])
