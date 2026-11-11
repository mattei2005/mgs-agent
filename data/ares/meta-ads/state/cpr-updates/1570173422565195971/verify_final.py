import importlib.util,json,sys,subprocess
from pathlib import Path
p=Path('/root/.hermes/profiles/ares/scripts/shein-g004-escalatepower-cpr-updates-20261111.py')
s=importlib.util.spec_from_file_location('verify_cpr',p);n=importlib.util.module_from_spec(s);s.loader.exec_module(n);b=n.b;root=b.ROOT
m=b.load(root/'manifest.json');d,delivery=b.helpers();dc=d.Discord()
rec=b.load(root/'runs/initial/delivery-0.json');part=b.load(root/'runs/initial/update-parts.json')[0]
r=dc.call('GET','/channels/'+b.TID+'/messages/'+rec['message_id']);assert r['content']==part and r['author']['id']==d.BOT_ID and r['channel_id']==b.TID
infra=dc.call('GET','/channels/1498132022634483894/messages/1570174762355916821');assert infra['channel_id']=='1498132022634483894' and infra['content']=='' and not infra.get('mentions') and not infra.get('mention_roles') and infra['embeds']
fields={x['name']:x['value'] for x in infra['embeds'][0]['fields']};assert b.REQUEST in fields['Motivo'] and m['scheduler_job_id'] in fields['Evidência']
jobs=b.load(Path('/root/.hermes/profiles/ares/cron/jobs.json'));jobs=jobs if isinstance(jobs,list) else jobs['jobs'];j=next(j for j in jobs if j['id']==m['scheduler_job_id']);assert j['enabled'] and j['no_agent'] and j['deliver']==j['failure_deliver']=='local'
b.save(root/'final-verification.json',{'first_message':r['id'],'report_infra_message':infra['id'],'job_id':j['id'],'enabled':j['enabled'],'no_agent':j['no_agent'],'next_run_at':j['next_run_at'],'slots':m['slots'],'expires_at':m['expires_at'],'post_schedule_pass':b.load(root/'schedule-post.json')['pass'],'campaign_count':len(m['campaigns']),'meta_writes':0})
print(json.dumps({'initial_delivery_get_verified':True,'report_infra_get_verified':True,'job_enabled':True,'next_run_at':j['next_run_at'],'last_slot':m['slots'][-1],'expires_at':m['expires_at'],'campaigns':[c['number'] for c in m['campaigns']]},ensure_ascii=False))
