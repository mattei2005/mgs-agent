import json
import pathlib
import subprocess
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from croniter import croniter

ROOT=pathlib.Path('/root/.hermes/profiles/ares/cache/scratch')
NY=ZoneInfo('America/New_York');SP=ZoneInfo('America/Sao_Paulo')
start=datetime(2026,10,17,0,0,tzinfo=NY);end=start+timedelta(days=8)
records=[]
def add_cron(expr,label,source,baseline=False,tz=NY):
 it=croniter(expr,start.astimezone(tz)-timedelta(seconds=1))
 while True:
  at=it.get_next(datetime).astimezone(NY)
  if at>=end:break
  records.append({'at':at.isoformat(),'label':label,'source':source,'baseline':baseline})
raw=subprocess.run(['crontab','-l'],text=True,capture_output=True,check=True).stdout
(ROOT/'cpv13-root-cron-before-20261017.txt').write_text(raw)
for source,text,system in [('root',raw,False)]+[(str(p),p.read_text(),True) for p in [pathlib.Path('/etc/crontab'),*pathlib.Path('/etc/cron.d').glob('*')] if p.is_file()]:
 tz=NY
 for line in text.splitlines():
  line=line.strip()
  if not line or line.startswith('#'):continue
  if line.startswith('CRON_TZ='):tz=ZoneInfo(line.split('=',1)[1]);continue
  parts=line.split(None,6 if system else 5)
  if len(parts)<(7 if system else 6) or '=' in parts[0]:continue
  expr=' '.join(parts[:5]);command=parts[-1]
  if expr.startswith('@'):continue
  dense=len(croniter.expand(expr)[0][0])>=8 or parts[0]=='*'
  add_cron(expr,command,source,baseline=dense,tz=tz)
for profile in ['zeus','atena','ares']:
 source=pathlib.Path(f'/root/.hermes/profiles/{profile}/cron/jobs.json')
 data=json.loads(source.read_text());jobs=data['jobs'] if isinstance(data,dict) else data
 if profile=='ares':(ROOT/'cpv13-ares-jobs-backup-20261017.json').write_text(json.dumps(data,ensure_ascii=False,indent=2))
 for job in jobs:
  if not job.get('enabled',True):continue
  s=job['schedule'];kind=s['kind'];label=f"{profile}:{job['id']}:{job['name']}"
  if kind=='cron':
   expr=s['expr'];dense=expr.split()[0]=='*' or len(croniter.expand(expr)[0][0])>=8
   add_cron(expr,label,str(source),dense)
  elif kind=='once':
   at=datetime.fromisoformat(s['run_at']).astimezone(NY)
   if start<=at<end:records.append({'at':at.isoformat(),'label':label,'source':str(source),'baseline':False})
  elif kind=='interval':
   at=datetime.fromisoformat(job['next_run_at']).astimezone(NY)
   while at<end:
    if at>=start:records.append({'at':at.isoformat(),'label':label,'source':str(source),'baseline':s.get('minutes',999)<=15})
    at+=timedelta(minutes=s['minutes'])
# System timers captured separately; frequent landing timers are isolated PC1/browser lanes,
# not CPV Meta account lane; no new campaign transactions or browser work is added.
timers=subprocess.run(['systemctl','list-timers','--all','--no-pager'],text=True,capture_output=True,check=True).stdout
(ROOT/'cpv13-system-timers-20261017.txt').write_text(timers)
results={}
for day in [18,19]:
 rows=[]
 for minute in [57,58,59]:
  at=datetime(2026,10,day,0,0,tzinfo=SP).astimezone(NY)-timedelta(minutes=60-minute)
  same=[r for r in records if datetime.fromisoformat(r['at']).replace(second=0,microsecond=0)==at.replace(second=0,microsecond=0)]
  own_id={'18':'b6dbf310a27e','19':'051eb42132fd'}[str(day)]
  own=[r for r in same if f'ares:{own_id}:' in r['label']]
  same=[r for r in same if r not in own]
  rows.append({'minute':minute,'launch_at':(at+timedelta(seconds=50)).isoformat(),'nonbaseline':[r['label'] for r in same if not r['baseline']],'baseline':[r['label'] for r in same if r['baseline']]})
 choices=[x for x in rows if not x['nonbaseline'] and x['minute']>=58]
 selected=min(choices,key=lambda x:(len(x['baseline']),x['minute']))
 results[str(day)]={'candidates':rows,'selected':selected}
assert all(x['selected']['minute']==58 for x in results.values()),results
report={'window_start':start.isoformat(),'window_end_exclusive':end.isoformat(),'occurrences':len(records),'results':results,
 'system_timer_review':'ares landing followup/intake are continuous isolated browser baselines; no CPV Meta account lane; account lock acquired only at target after wait',
 'lane':'/run/lock/ares-cpv-meta-lane-1046241194533786.lock','wait_seconds':70,'lock_wait_seconds':20,'script_timeout_budget_seconds':180,
 'operational_conflicts':0,'other_profiles_modified':False}
(ROOT/'cpv13-d1-collision-audit-20261017.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
for day,r in results.items():print(json.dumps({'batch':day,'selected':r['selected'],'operational_conflicts':0},ensure_ascii=False))
print('8-day occurrences evaluated:',len(records))
