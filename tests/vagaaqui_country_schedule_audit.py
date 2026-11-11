import datetime as dt,json,subprocess,pathlib,importlib.util
from zoneinfo import ZoneInfo
from croniter import croniter
ROOT=pathlib.Path('/root/mgs-agent'); ET=ZoneInfo('America/New_York'); UTC=dt.timezone.utc
now=dt.datetime.now(ET); begin=now.replace(hour=0,minute=0,second=0,microsecond=0);end=begin+dt.timedelta(days=8)
entries=[]
def add_text(text,source,system=False):
 tz=ET
 for line in text.splitlines():
  s=line.strip()
  if not s or s.startswith('#'):continue
  if s.startswith('CRON_TZ='):tz=ZoneInfo(s.split('=',1)[1]);continue
  parts=s.split(None,6 if system else 5)
  if len(parts)<(7 if system else 6):continue
  expr=' '.join(parts[:5]);cmd=parts[-1]
  if croniter.is_valid(expr):entries.append(dict(expr=expr,tz=tz,source=source,cmd=cmd))
root=subprocess.check_output(['crontab','-l'],text=True);add_text(root,'root')
for p in [pathlib.Path('/etc/crontab'),*pathlib.Path('/etc/cron.d').glob('*')]:
 if p.is_file():add_text(p.read_text(),str(p),True)
intervals=[]
for p in [pathlib.Path('/root/.hermes/cron/jobs.json'),*pathlib.Path('/root/.hermes/profiles').glob('*/cron/jobs.json')]:
 if not p.exists():continue
 data=json.loads(p.read_text());jobs=data.get('jobs',[]) if isinstance(data,dict) else data
 for j in jobs:
  if not j.get('enabled',True):continue
  s=j.get('schedule',{}); base=dict(source=str(p)+':'+j['id'],cmd=j.get('name',''),tz=ET)
  if s.get('kind')=='cron':entries.append(dict(base,expr=s['expr']))
  elif j.get('next_run_at'):
   t=dt.datetime.fromisoformat(j['next_run_at']);delta=dt.timedelta(minutes=s.get('minutes',0))
   while t<end:
    if t>=begin:intervals.append(dict(base,at=t))
    if delta.total_seconds()<=0:break
    t+=delta
# Only infrastructure predicates can be dense baseline exceptions.
baseline_names=['sync-souls','monitor-auto-push','check-pending-reports','monitor-service-restarts','monitor-tool-loops','track-article-cost','monitor-cron-stale-logs','hermes-news-explainer','monitor_honcho_billing_watch','discord-archive-stale-agent-threads','monitor-vps-health','alerts-infra-failed-alert-resolver','monitor_hermes_pending_writes','finalize-hermes-structural-write','monitor-hermes-memory-capacity','meta-app-roles-watch','b013-dtr-link-watch','MGS DR monitor SLA','sysstat','sessionclean']
def baseline(e):return any(x in e['cmd'] for x in baseline_names)
occupied={};all_events=[]
for e in entries:
 # Host cron has observed host-TZ semantics; also check declared timezone.
 zones={str(e['tz']):e['tz']}
 if e['source']=='root':zones[str(ET)]=ET
 for tz in zones.values():
  it=croniter(e['expr'],begin.astimezone(tz)-dt.timedelta(seconds=1)); t=it.get_next(dt.datetime)
  while t<end.astimezone(tz):
   local=t.astimezone(ET).replace(second=0,microsecond=0);item=dict(e,at=local,baseline=baseline(e));all_events.append(item);occupied.setdefault(local,[]).append(item);t=it.get_next(dt.datetime)
for e in intervals:
 local=e['at'].astimezone(ET).replace(second=0,microsecond=0);occupied.setdefault(local,[]).append(dict(e,baseline=False))
scores=[]
for minute in range(60):
 points=[begin+dt.timedelta(days=d,hours=h,minutes=minute) for d in range(8) for h in range(24)]
 collisions=[e for t in points for e in occupied.get(t,[]) if not e['baseline'] and 'monitor-vagaaqui-country.py' not in e['cmd']]
 bases=[e for t in points for e in occupied.get(t,[]) if e['baseline']]
 if not collisions:scores.append((len(bases),minute,sorted(set(e['cmd'] for e in bases))))
assert scores,'no hourly slot available'
scores.sort();selected=scores[0]
timers=subprocess.check_output(['systemctl','list-timers','--all','--no-pager'],text=True)
# Timer activations are host-maintenance with jitter, not deterministic business writers.
registered=json.loads((ROOT/'data/infra-inventory.json').read_text())
app_crons=[r.get('entry') for r in registered.get('crons',[]) if r.get('entry') and r['entry'] in root]
result={'generated_at':now.isoformat(),'days':8,'window_start':begin.isoformat(),'window_end':end.isoformat(),'sources':sorted(set(e['source'] for e in entries)), 'cron_definitions':len(entries),'registered_live_crons':len(app_crons),'systemd_timers':timers,'hourly_candidates':[{'minute':m,'baseline_occurrences':n} for n,m,b in scores], 'selected_minute':selected[1],'baseline_commands':selected[2], 'operational_collisions':0,'shared_resources':'New dedicated lock/state; no browser; CF read-only one credential lookup only when a daily bucket is due; Discord same thread. Dense baselines are local predicates, not a second writer. +7s deterministic stagger.'}
p=ROOT/'data/vagaaqui-country-monitor';p.mkdir(exist_ok=True);(p/'schedule-preflight.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ['sources','systemd_timers']},ensure_ascii=False))
