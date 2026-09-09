"""Eight-day global scheduler preflight for a chosen Eastern hour; read-only."""
import pathlib,json,subprocess,datetime,re,sys,argparse
from zoneinfo import ZoneInfo
from croniter import croniter
ap=argparse.ArgumentParser();ap.add_argument('minute',type=int,nargs='?');ap.add_argument('--hour',type=int,default=7);ap.add_argument('--output-dir',type=pathlib.Path,default=pathlib.Path('/root/mgs-agent/apps/finance-system/private/spend-import-1546991137171181578'));args=ap.parse_args();assert 0<=args.hour<=23 and (args.minute is None or 0<=args.minute<=59)
TZ=ZoneInfo('America/New_York');now=datetime.datetime.now(TZ);start=now.replace(hour=0,minute=0,second=0,microsecond=0);end=start+datetime.timedelta(days=8);D=args.output_dir;D.mkdir(parents=True,exist_ok=True,mode=0o700);RUNNER='finance_media_spend_sync.py';entries=[];unknown=[]
def cron_dates(expr,tz=TZ):
 it=croniter(expr,start.astimezone(tz)-datetime.timedelta(seconds=1));out=[]
 while True:
  t=it.get_next(datetime.datetime).astimezone(TZ)
  if t>=end:return out
  if t>=start:out.append(t)
def push(source,name,ds,expr=None,baseline=None):
 entries.append({'source':source,'name':name,'schedule':expr,'ticks':ds,'baseline':baseline if baseline is not None else len(ds)>=8*24*4 and source!='ares' and not name.startswith(('ares_','sb-broadcast'))})
raw=[('root',subprocess.run(['crontab','-l'],capture_output=True,text=True,check=True).stdout)]+[(str(p),p.read_text()) for p in [pathlib.Path('/etc/crontab'),*pathlib.Path('/etc/cron.d').glob('*')] if p.is_file()]
for source,text in raw:
 for line in text.splitlines():
  line=line.strip();parts=line.split()
  if not parts or line.startswith('#') or RUNNER in line:continue
  if len(parts)>=6 and (line[0].isdigit() or line[0]=='*'):
   expr=' '.join(parts[:5]);name=next((pathlib.Path(x).name for x in parts[5:] if x.endswith(('.py','.sh'))),next((pathlib.Path(x).name for x in parts[5:] if '.lock' in x),'system'));push(source,name,cron_dates(expr),expr)
  elif line.startswith('@') and not line.startswith('@reboot'):unknown.append({'source':source,'reason':'unparsed_calendar'})
profiles=list(pathlib.Path('/root/.hermes/profiles').glob('*/cron/jobs.json'))+[pathlib.Path('/root/.hermes/cron/jobs.json')]
for p in profiles:
 if not p.exists():continue
 data=json.loads(p.read_text());jobs=data if isinstance(data,list) else data.get('jobs',[])
 for job in jobs:
  if not job.get('enabled',True) or job.get('state') in ['paused','completed','cancelled']:continue
  s=job['schedule'];name=job.get('name',job['id']);source=p.parent.parent.name;tz=ZoneInfo(job.get('timezone') or 'America/New_York');ds=[]
  if s.get('expr'):ds=cron_dates(s['expr'],tz)
  elif s.get('minutes') and job.get('next_run_at'):
   step=datetime.timedelta(minutes=s['minutes']);t=datetime.datetime.fromisoformat(job['next_run_at']).astimezone(TZ)
   while t>=start:t-=step
   while t<end:
    if t>=start:ds.append(t)
    t+=step
  elif job.get('next_run_at'):
   t=datetime.datetime.fromisoformat(job['next_run_at']).astimezone(TZ)
   if start<=t<end:ds=[t]
  else:unknown.append({'source':source,'name':name,'reason':'unparsed_job_schedule'})
  push(source,name,ds,s)
os_timers={'sysstat-collect','phpsessionclean','ua-timer','fwupd-refresh','dpkg-db-backup','logrotate','sysstat-summary','apt-daily','motd-news','apt-daily-upgrade','man-db','update-notifier-download','systemd-tmpfiles-clean','update-notifier-motd','e2scrub_all','fstrim','apport-autoreport','snapd.snap-repair'}
lines=subprocess.run(['systemctl','list-units','--type=timer','--all','--no-legend','--no-pager'],capture_output=True,text=True,check=True).stdout.splitlines();timers=[]
for line in lines:
 names=[x for x in line.split() if x.endswith('.timer')]
 if not names:continue
 unit=names[0];base=unit[:-6];show=subprocess.run(['systemctl','show',unit,'-p','TimersCalendar','-p','TimersMonotonic','-p','RandomizedDelayUSec'],capture_output=True,text=True,check=True).stdout;timers.append({'unit':unit,'definition':show.strip(),'os_baseline':base in os_timers})
 if base not in os_timers:unknown.append({'source':'systemd','name':unit,'reason':'custom_timer_requires_classification'})
 for expr in re.findall(r'OnCalendar=([^;]+)',show):
  p=subprocess.run(['systemd-analyze','calendar','--iterations=2000','--base-time='+start.isoformat(),expr.strip()],capture_output=True,text=True,timeout=25)
  if p.returncode:unknown.append({'source':'systemd','name':unit,'reason':'calendar_expansion_failed'});continue
  ds=[]
  for stamp in re.findall(r'(?:Next elapse|Iter\. #\d+):[^\n]*?(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})',p.stdout):
   t=datetime.datetime.fromisoformat(stamp).replace(tzinfo=TZ)
   if start<=t<end:ds.append(t)
  push('systemd',unit,ds,expr.strip(),True)
def conflicts(minute):
 keys={t.strftime('%Y-%m-%d %H:%M') for t in cron_dates(f'{minute} {args.hour} * * *')};ops=[];base=[]
 for e in entries:
  n=sum(t.strftime('%Y-%m-%d %H:%M') in keys for t in e['ticks'])
  if n:(base if e['baseline'] else ops).append({'source':e['source'],'name':e['name'],'collisions':n})
 return ops,base
candidates=[]
for minute in range(0,60):
 ops,base=conflicts(minute);candidates.append({'minute':minute,'ops':ops,'baseline':base,'baseline_count':sum(x['collisions'] for x in base)})
free=[x for x in candidates if not x['ops']];assert free and not unknown,unknown
chosen=min(free,key=lambda x:(x['baseline_count'],x['minute']));requested=args.minute if args.minute is not None else chosen['minute'];ops,base=conflicts(requested);report={'pass':not ops and not unknown,'schedule':f'{requested} {args.hour} * * *','timezone':str(TZ),'civil_dates':8,'operational_conflicts':ops,'baseline_collisions':base,'stagger_seconds':25,'candidate_summary':[{'minute':x['minute'],'operational_conflicts':len(x['ops']),'baseline_count':x['baseline_count']} for x in candidates],'resource_guards':['own media-spend-sync.lock','quote-sync.lock only for optimistic financial publish','read-only shared Meta and SA clients;3workers; no browser or ad writes'],'timers':timers,'jobs':[{k:v for k,v in e.items() if k!='ticks'}|{'expanded_ticks':len(e['ticks'])} for e in entries],'self_excluded_only_for_postwrite_collision_check':RUNNER,'custom_scheduler_scope':'MGS root and /etc cron, every profile job file, active systemd timers; existing finance auxiliary long-poll worker is event-driven and serialized by quote lock'};p=D/('schedule-post.json' if args.minute is not None else 'schedule-preflight.json');p.write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k not in ['jobs','timers','candidate_summary']}));assert report['pass']
