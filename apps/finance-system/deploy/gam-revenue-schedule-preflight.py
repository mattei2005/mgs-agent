#!/usr/bin/env python3
"""Global eight-day collision audit for the daily GAM email window."""
import argparse
import datetime
import json
import pathlib
import re
import subprocess
from zoneinfo import ZoneInfo

parser=argparse.ArgumentParser();parser.add_argument('--minutes');parser.add_argument('--finalize-minutes');parser.add_argument('--output-dir',type=pathlib.Path,required=True);args=parser.parse_args()
TZ=ZoneInfo('America/New_York');now=datetime.datetime.now(TZ);start=now.replace(hour=0,minute=0,second=0,microsecond=0);end=start+datetime.timedelta(days=8);D=args.output_dir;D.mkdir(parents=True,exist_ok=True,mode=0o700);RUNNER='finance_gam_revenue_sync.py';entries=[];unknown=[]
def field_match(token,value,low,high,names=None,dow=False):
 names=names or {}
 def number(raw):
  key=raw.lower();result=names.get(key,int(raw) if raw.isdigit() else None)
  if result is None:raise ValueError('unsupported cron token '+raw)
  return 0 if dow and result==7 else result
 for part in token.split(','):
  base,step=(part.split('/',1)+['1'])[:2] if '/' in part else (part,'1');step=int(step)
  if base=='*':first,last=low,high
  elif '-' in base:
   left,right=base.split('-',1);first,last=number(left),number(right)
  else:first=last=number(base)
  if first<=value<=last and (value-first)%step==0:return True
 return False
def cron_matches(expression,value):
 minute,hour,dom,month,dow=expression.split();months={name:i for i,name in enumerate(['jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec'],1)};days={name:i for i,name in enumerate(['mon','tue','wed','thu','fri','sat'],1)}|{'sun':0}
 if not field_match(minute,value.minute,0,59) or not field_match(hour,value.hour,0,23) or not field_match(month,value.month,1,12,months):return False
 dom_ok=field_match(dom,value.day,1,31);cron_dow=(value.weekday()+1)%7;dow_ok=field_match(dow,cron_dow,0,7,days,True)
 return dom_ok and dow_ok if dom=='*' or dow=='*' else dom_ok or dow_ok
def cron_dates(expr,tz=TZ):
 out=[];value=start
 while value<end:
  if cron_matches(expr,value.astimezone(tz)):out.append(value)
  value+=datetime.timedelta(minutes=1)
 return out
def push(source,name,dates,schedule=None,baseline=None):entries.append({'source':source,'name':name,'schedule':schedule,'ticks':dates,'baseline':baseline if baseline is not None else len(dates)>=8*24*4 and source!='ares' and not name.startswith(('ares_','sb-broadcast'))})
raw=[('root',subprocess.run(['crontab','-l'],capture_output=True,text=True,check=True).stdout)]+[(str(path),path.read_text()) for path in [pathlib.Path('/etc/crontab'),*pathlib.Path('/etc/cron.d').glob('*')] if path.is_file()]
for source,text in raw:
 for line in text.splitlines():
  line=line.strip();parts=line.split()
  if not parts or line.startswith('#') or RUNNER in line:continue
  if len(parts)>=6 and (line[0].isdigit() or line[0]=='*'):
   expression=' '.join(parts[:5]);name=next((pathlib.Path(x).name for x in parts[5:] if x.endswith(('.py','.sh'))),next((pathlib.Path(x).name for x in parts[5:] if '.lock' in x),'system'));push(source,name,cron_dates(expression),expression)
  elif line.startswith('@') and not line.startswith('@reboot'):unknown.append({'source':source,'reason':'unparsed_calendar'})
profiles=list(pathlib.Path('/root/.hermes/profiles').glob('*/cron/jobs.json'))+[pathlib.Path('/root/.hermes/cron/jobs.json')]
for path in profiles:
 if not path.exists():continue
 data=json.loads(path.read_text());jobs=data if isinstance(data,list) else data.get('jobs',[])
 for job in jobs:
  if not job.get('enabled',True) or job.get('state') in ['paused','completed','cancelled']:continue
  schedule=job['schedule'];name=job.get('name',job['id']);source=path.parent.parent.name;timezone=ZoneInfo(job.get('timezone') or 'America/New_York');dates=[]
  if schedule.get('expr'):dates=cron_dates(schedule['expr'],timezone)
  elif schedule.get('minutes') and job.get('next_run_at'):
   step=datetime.timedelta(minutes=schedule['minutes']);value=datetime.datetime.fromisoformat(job['next_run_at']).astimezone(TZ)
   while value>=start:value-=step
   while value<end:
    if value>=start:dates.append(value)
    value+=step
  elif job.get('next_run_at'):
   value=datetime.datetime.fromisoformat(job['next_run_at']).astimezone(TZ)
   if start<=value<end:dates=[value]
  else:unknown.append({'source':source,'name':name,'reason':'unparsed_job_schedule'})
  push(source,name,dates,schedule)
os_timers={'sysstat-collect','phpsessionclean','ua-timer','fwupd-refresh','dpkg-db-backup','logrotate','sysstat-summary','apt-daily','motd-news','apt-daily-upgrade','man-db','update-notifier-download','systemd-tmpfiles-clean','update-notifier-motd','e2scrub_all','fstrim','apport-autoreport','snapd.snap-repair'}
for line in subprocess.run(['systemctl','list-units','--type=timer','--all','--no-legend','--no-pager'],capture_output=True,text=True,check=True).stdout.splitlines():
 names=[x for x in line.split() if x.endswith('.timer')]
 if not names:continue
 unit=names[0];base=unit[:-6];show=subprocess.run(['systemctl','show',unit,'-p','TimersCalendar','-p','TimersMonotonic','-p','RandomizedDelayUSec'],capture_output=True,text=True,check=True).stdout
 if base not in os_timers:unknown.append({'source':'systemd','name':unit,'reason':'custom_timer_requires_classification'})
 for expression in re.findall(r'OnCalendar=([^;]+)',show):
  result=subprocess.run(['systemd-analyze','calendar','--iterations=2000','--base-time='+start.isoformat(),expression.strip()],capture_output=True,text=True,timeout=25);dates=[]
  if result.returncode:unknown.append({'source':'systemd','name':unit,'reason':'calendar_expansion_failed'});continue
  for stamp in re.findall(r'(?:Next elapse|Iter\. #\d+):[^\n]*?(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})',result.stdout):
   value=datetime.datetime.fromisoformat(stamp).replace(tzinfo=TZ)
   if start<=value<end:dates.append(value)
  push('systemd',unit,dates,expression.strip(),True)
def conflicts(minute,hour):
 target={x.strftime('%Y-%m-%d %H:%M') for x in cron_dates(f'{minute} {hour} * * *')};ops=[];baseline=[]
 for entry in entries:
  count=sum(value.strftime('%Y-%m-%d %H:%M') in target for value in entry['ticks'])
  if count:(baseline if entry['baseline'] else ops).append({'source':entry['source'],'name':entry['name'],'collisions':count})
 return ops,baseline
candidates=[]
for hour,minute_range in [(8,range(31)),(9,range(15,46))]:
 for minute in minute_range:
  ops,baseline=conflicts(minute,hour);candidates.append({'hour':hour,'minute':minute,'operational_conflicts':ops,'baseline_collisions':baseline,'baseline_count':sum(x['collisions'] for x in baseline)})
if args.minutes:selected=[int(x) for x in args.minutes.split(',')]
else:
 selected=[]
 for low,high in [(0,5),(10,15),(20,25),(28,30)]:
  pool=[x for x in candidates if x['hour']==8 and low<=x['minute']<=high and not x['operational_conflicts']]
  if not pool:raise AssertionError('no free minute in requested poll band')
  selected.append(min(pool,key=lambda x:(x['baseline_count'],x['minute']))['minute'])
if args.finalize_minutes:finalize=[int(x) for x in args.finalize_minutes.split(',')]
else:
 finalize=[]
 for low,high in [(20,25),(30,35),(40,45)]:
  pool=[x for x in candidates if x['hour']==9 and low<=x['minute']<=high and not x['operational_conflicts']]
  if not pool:raise AssertionError('no free minute in finalize retry band')
  finalize.append(min(pool,key=lambda x:(x['baseline_count'],x['minute']))['minute'])
assert selected==sorted(set(selected)) and all(0<=x<=30 for x in selected)
assert finalize==sorted(set(finalize)) and all(15<=x<=45 for x in finalize)
checks=[next(x for x in candidates if x['hour']==8 and x['minute']==minute) for minute in selected]+[next(x for x in candidates if x['hour']==9 and x['minute']==minute) for minute in finalize];report={'pass':not unknown and all(not x['operational_conflicts'] for x in checks),'schedule':','.join(map(str,selected))+' 8 * * *','poll_minutes':selected,'finalize_schedule':','.join(map(str,finalize))+' 9 * * *','finalize_minutes':finalize,'timezone':str(TZ),'civil_dates':8,'operational_conflicts':[x for check in checks for x in check['operational_conflicts']],'baseline_collisions':[{'hour':check['hour'],'minute':check['minute'],**row} for check in checks for row in check['baseline_collisions']],'unknown':unknown,'resource_guards':['own flock lock','intake never advances cutoff','spend-state gate plus remote spend-ledger gate','quote-sync lock around rehearsal/backup/apply','read-only IMAP BODY.PEEK','one 1Password credential resolution per run','transaction revision guard and deterministic source identity'],'candidate_summary':[{'hour':x['hour'],'minute':x['minute'],'operational_conflicts':len(x['operational_conflicts']),'baseline_count':x['baseline_count']} for x in candidates]};path=D/('schedule-post.json' if args.minutes and args.finalize_minutes else 'schedule-preflight.json');path.write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='candidate_summary'}));assert report['pass']
