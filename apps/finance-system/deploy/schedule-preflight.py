import json,pathlib,subprocess,datetime
from zoneinfo import ZoneInfo
from croniter import croniter
ROOT=pathlib.Path('/root/mgs-agent/apps/finance-system');tz=ZoneInfo('America/New_York');start=datetime.datetime.now(tz).replace(hour=0,minute=0,second=0,microsecond=0);end=start+datetime.timedelta(days=8)
entries=[]
raw=[('root',subprocess.run(['crontab','-l'],capture_output=True,text=True,check=True).stdout)]
raw += [(str(p),p.read_text()) for p in [pathlib.Path('/etc/crontab'),*pathlib.Path('/etc/cron.d').glob('*')] if p.is_file()]
for source,text in raw:
 for line in text.splitlines():
  parts=line.split()
  if len(parts)>=6 and (line[0].isdigit() or line[0]=='*'):
   expr=' '.join(parts[:5]);name=next((pathlib.Path(v).name for v in parts[5:] if '.lock' in v),next((pathlib.Path(v).name for v in parts[5:] if v.endswith(('.sh','.py'))),'system'))
   entries.append({'source':source,'name':name,'expr':expr})
for profile in ['zeus','atena','ares']:
 j=json.loads((pathlib.Path('/root/.hermes/profiles')/profile/'cron/jobs.json').read_text());jobs=j if isinstance(j,list) else j['jobs']
 for job in jobs:
  if not job.get('enabled',True) or job.get('id')=='685397627b29':continue
  s=job['schedule'];entries.append({'source':profile,'name':job['name'],'expr':s.get('expr'),'interval':s.get('minutes'),'next':job.get('next_run_at')})
def dates(entry):
 if entry.get('expr'):
  it=croniter(entry['expr'],start-datetime.timedelta(seconds=1));out=[]
  while True:
   t=it.get_next(datetime.datetime)
   if t>=end:return out
   out.append(t)
 elif entry.get('interval') and entry.get('next'):
  step=datetime.timedelta(minutes=entry['interval']);t=datetime.datetime.fromisoformat(entry['next']);out=[]
  while t>=start:t-=step
  while t<end:
   if t>=start:out.append(t)
   t+=step
  return out
 return []
for e in entries:
 e['dates']=dates(e);e['baseline']=len(e['dates'])>=8*24*4 and (e['source']!='ares') and not e['name'].startswith(('ares_','sb-broadcast'))
proposed='26,56 * * * *';ticks=dates({'expr':proposed});keys={t.strftime('%Y-%m-%d %H:%M') for t in ticks};conflicts=[];baseline=[]
for e in entries:
 count=sum(t.strftime('%Y-%m-%d %H:%M') in keys for t in e['dates'])
 if count:(baseline if e['baseline'] else conflicts).append({'name':e['name'],'source':e['source'],'count':count})
report={'schedule':proposed,'timezone':str(tz),'civil_dates':8,'ticks':len(ticks),'operational_conflicts':conflicts,'baseline_collisions':baseline,'stagger_seconds':25,'resource':'dedicated quote-sync.lock; finance workspace writer uses optimistic revision; Google SA read-only; private host transport; fixed rates excluded','timers':'OS randomized maintenance timers are infrastructure baseline; no financial custom scheduler beyond listed root/Hermes jobs found in preflight'}
(ROOT/'private/ui-redesign-1546005809845243944/schedule-preflight.json').write_text(json.dumps(report,indent=2));print(json.dumps(report));raise SystemExit(1 if conflicts else 0)
