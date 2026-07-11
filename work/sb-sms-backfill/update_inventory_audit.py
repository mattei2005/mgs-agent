#!/usr/bin/env python3
import json,os,hashlib
from datetime import datetime,timezone
inv_path='/root/mgs-agent/data/infra-inventory.json'
log_path='/root/mgs-agent/logs/events-audit.jsonl'
root='/tmp/mgs-quiz-carro-audit/mgs-quiz-carro'
def meta(rel):
    p=os.path.join(root,rel); b=open(p,'rb').read()
    return {'path':rel,'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}
with open(inv_path) as f:
    data=json.load(f)
matches=[x for x in data.setdefault('runtime_artifacts',[]) if x.get('plugin')=='mgs-quiz-carro' and x.get('site')=='creditoparaveiculo.com']
if len(matches)!=1:
    raise SystemExit(f'expected one artifact, got {len(matches)}')
artifact=matches[0]
artifact.update({
    'id':'creditoparaveiculo-mgs-quiz-carro-1.7.0-20260710',
    'version':'1.7.0',
    'db_version':'1.3.0',
    'feature':'Quiz car BR + custo estimado SMS base WP + receita líquida Smart Bidding por período',
    'package_sha256':'4271b1b79df0bc9d992194c31b222772dcb358a93b0028ccdf97147174fbce8a',
    'backup_path':'/home/runcloud2/backups/creditoparaveiculo/mgs-quiz-carro-1.6.2-20260711T011008Z',
    'files':[meta('mgs-quiz-carro.php'),meta('includes/class-mgs-quiz-admin.php'),meta('includes/class-mgs-quiz-activator.php')],
    'sms_revenue_backfill':{
        'table':'wp_mgs_quiz_sms_revenue','metric':'NET_REVENUE BRL (Discount revenue share enabled)',
        'publisher':'digital-trust_creditoparaveiculo','domain':'creditoparaveiculo',
        'groups':61,'source_rows':61,'dates':49,'first_date':'2026-05-22','last_date':'2026-07-09',
        'gross_revenue_cents':1392373,'net_revenue_cents':1253137,'cron_created':False,
    },
    'validation':'PHP lint 11/11; schema 1.3.0; idempotent import/readback 61 rows/49 dates; historical net R$ 12.531,37; 2026-07-08 R$ 274,57; empty-state smoke; four quiz routes HTTP 200',
    'updated_at':datetime.now(timezone.utc).isoformat(),
})
data['updated_at']=datetime.now(timezone.utc).isoformat()
tmp=inv_path+'.tmp'
with open(tmp,'w') as f:
    json.dump(data,f,ensure_ascii=False,indent=2); f.write('\n')
with open(tmp) as f:
    json.load(f)
os.replace(tmp,inv_path)
event={
    'timestamp':datetime.now(timezone.utc).isoformat(),'event':'mgs_quiz_sms_revenue_backfill_completed','actor':'zeus',
    'site':'creditoparaveiculo.com','plugin':'mgs-quiz-carro','version':'1.7.0','db_version':'1.3.0',
    'publisher':'digital-trust_creditoparaveiculo','period':{'from':'2026-05-22','to':'2026-07-09'},
    'source_rows':61,'stored_groups':61,'dates':49,'gross_revenue_cents':1392373,'net_revenue_cents':1253137,
    'package_sha256':artifact['package_sha256'],'backup_path':artifact['backup_path'],
    'validation':'BACKFILL_OK + REVENUE_REPORT_SMOKE_OK + 4 public routes HTTP 200','cron_created':False,
}
with open(log_path,'a') as f:
    f.write(json.dumps(event,ensure_ascii=False)+'\n')
print('INVENTORY_AUDIT_OK',artifact['version'],artifact['files'][1]['sha256'][:12])
