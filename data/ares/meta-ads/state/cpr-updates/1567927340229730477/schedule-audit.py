#!/usr/bin/env python3
"""Request-local schedule audit; no scheduler mutation."""
import json,sys,types
from pathlib import Path
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
from croniter import croniter
ROOT=Path('/root/mgs-agent/data/ares/meta-ads/state/cpr-updates/1567927340229730477')
SOURCE=Path('/root/.hermes/profiles/ares/scripts/shein-daily-schedule-audit.py')
src=SOURCE.read_text()
old="""        itr=croniter(expr,start.astimezone(tz)-timedelta(seconds=1));out=[]
        for _ in range(12000):
            t=itr.get_next(datetime)
            if t>=end:return out
            out.append(t.astimezone(NY))
        raise RuntimeError('schedule expansion limit')"""
new="""        local_start=start.astimezone(tz).replace(tzinfo=None)
        local_end=end.astimezone(tz).replace(tzinfo=None)
        itr=croniter(expr,local_start-timedelta(seconds=1));out=[]
        for _ in range(13000):
            naive=itr.get_next(datetime)
            if naive>=local_end:return out
            seen=set()
            for fold in (0,1):
                aware=naive.replace(tzinfo=tz,fold=fold)
                utc=aware.astimezone(ZoneInfo('UTC'))
                if utc.astimezone(tz).replace(tzinfo=None)!=naive or utc in seen:continue
                seen.add(utc)
                if start<=utc.astimezone(NY)<end:out.append(utc.astimezone(NY))
        raise RuntimeError('schedule expansion limit')"""
assert old in src
src=src.replace("'name':j.get('name',j['id'])", "'job_id':j['id'],'name':j.get('name',j['id'])")
mod=types.ModuleType('audit_request');exec(compile(src.replace(old,new),str(SOURCE),'exec'),mod.__dict__)
raw=mod.inventory()
infra=('monitor-tool-loops','monitor-service-restarts','monitor-hermes-memory-capacity','monitor-vps-health','sync-souls','monitor-cron-stale-logs','monitor_honcho','alerts-infra-failed-alert-resolver','monitor_hermes_pending_writes','finalize-hermes-structural-write','hermes-news-explainer-watchdog','hermes-usage-alert','hermes-context','honcho','watchdog','reconcile-hermes')
for e in raw['entries']:
 if e['baseline'] and e['source']!='systemd':
  e['baseline']=any(x in e['name'] for x in infra)

ROOT.mkdir(parents=True,exist_ok=True)
(ROOT/('global-schedule-after.json' if '--post' in sys.argv else 'global-schedule-before.json')).write_text(json.dumps(raw,ensure_ascii=False,indent=2))
ny=ZoneInfo('America/New_York');now=datetime.now(ny);end=datetime(2026,11,6,tzinfo=ny)
manifest_path=ROOT/'manifest.json'
manifest=json.loads(manifest_path.read_text()) if manifest_path.exists() else None
own='SHEIN G004 Yolokfx04 relatorios CPR 05-11'
def assess(minutes):
 ticks=[];t=now.replace(second=0,microsecond=0)+timedelta(minutes=1)
 while t<end:
  if t.minute in minutes:ticks.append(t)
  t+=timedelta(minutes=1)
 keys={t.strftime('%Y-%m-%d %H:%M') for t in ticks};ops=[];base=[]
 for e in raw['entries']:
  if manifest and e.get('job_id')==manifest.get('scheduler_job_id'):continue
  hits=[s for s in e['ticks'] if datetime.fromisoformat(s).strftime('%Y-%m-%d %H:%M') in keys]
  if hits:(base if e['baseline'] else ops).append({'source':e['source'],'name':e['name'],'hits':len(hits)})
 return {'minutes':minutes,'ticks':[t.isoformat() for t in ticks],'operational_conflicts':ops,'baselines':base,'baseline_hits':sum(v['hits'] for v in base)}
choices=[assess([m,m+30]) for m in range(30)]
valid=[c for c in choices if not c['operational_conflicts']]
assert valid and not raw['unknown']
chosen=assess(manifest['minutes']) if '--post' in sys.argv else min(valid,key=lambda c:(c['baseline_hits'],c['minutes']))
assert not chosen['operational_conflicts']
result={'pass':True,'generated_at':now.isoformat(),'horizon':raw['horizon'],'eight_civil_dates_expanded':True,'selection':chosen,'unknown':raw['unknown'],'own_entries':sum(e['name']==own for e in raw['entries']),'resource_review':{'lock':'request-specific flock','timeout_seconds':165,'account_ids':['781612907182683'],'Meta':'GET only with existing quota/throttle helper; bounded single source','Discord':'one thread; nonce and exact GET','browser':False,'SB':False,'other_schedulers_unchanged':True,'baseline_exception':'independent infra baseline locks/states; no account writer or report lock shared'}}
(ROOT/('schedule-post-check.json' if '--post' in sys.argv else 'schedule-pre-check.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2))
print(json.dumps(result,ensure_ascii=False))