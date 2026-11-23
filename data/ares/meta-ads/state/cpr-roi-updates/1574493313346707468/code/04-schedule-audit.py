#!/usr/bin/env python3
"""Finite schedule allocator; global inventory is read-only."""
import argparse,json,subprocess,importlib.util,sys,shutil
from pathlib import Path
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
from croniter import croniter
R=Path('/root/mgs-agent/data/ares/meta-ads/state/cpr-roi-updates/1574493313346707468');Z=ZoneInfo('America/New_York')
P=Path('/root/mgs-agent/data/ares/meta-ads/state/cpr-updates/1570877060862312680/schedule-audit.py')
s=importlib.util.spec_from_file_location('inventory14',P);assert s and s.loader;mod=importlib.util.module_from_spec(s);sys.modules[s.name]=mod;s.loader.exec_module(mod)
def audit(post=False):
 raw=mod.inventory();m=json.loads((R/'manifest.json').read_text());now=datetime.now(Z);end=datetime.fromisoformat(m['expires_at']);initial=json.loads((R/'runs'/m.get('schedule_reference_run','initial')/'complete.json').read_text());first=datetime.fromisoformat(initial['observed_at'])
 infra=('monitor-tool-loops','monitor-service-restarts','monitor-hermes-memory-capacity','monitor-vps-health','sync-souls','monitor-cron-stale-logs','monitor_honcho','alerts-infra-failed-alert-resolver','monitor_hermes_pending_writes','finalize-hermes-structural-write','hermes-news-explainer-watchdog','hermes-usage-alert','hermes-context','honcho','watchdog','reconcile-hermes')
 for e in raw['entries']:
  if e['baseline'] and e['source']!='systemd':
   e['baseline']=any(x in e['name'] for x in infra)
   if e['source']=='root' and e['name']=='hermes-news-explainer.py':e['baseline']=True;e['baseline_evidence']='Independent release-announcement monitor, dedicated state/flock, no Meta/SB or report lock'
   if e['source']=='/etc/cron.d/sysstat' and e.get('command')=='root command -v debian-sa1 > /dev/null && debian-sa1 1 1':e['baseline']=True;e['baseline_evidence']='Dense OS statistics collector, independent state'
 def assess(minute):
  expr=f'{minute},{minute+30} * 23 11 *';it=croniter(expr,now);ticks=[]
  for _ in range(49):
   t=it.get_next(datetime)
   if t>=end:break
   ticks.append(t)
  keys={t.strftime('%Y-%m-%d %H:%M') for t in ticks};ops=[];base=[]
  for e in raw['entries']:
   if e['source']=='ares' and e.get('job_id')==m.get('scheduler_job_id'):continue
   hits=[s for s in e['ticks'] if datetime.fromisoformat(s).strftime('%Y-%m-%d %H:%M') in keys]
   if hits:(base if e['baseline'] or e.get('no_op_verified') else ops).append({'scheduler':e['source'],'job_id':e.get('job_id'),'name':e['name'],'hits':len(hits),'no_op_verified':e.get('no_op_verified',False)})
  return {'minutes':[minute,minute+30],'ticks':[t.isoformat() for t in ticks],'operational_conflicts':ops,'baselines':base,'baseline_hits':sum(x['hits'] for x in base)}
 opts=[assess(i) for i in range(30)];valid=[v for v in opts if v['ticks'] and not v['operational_conflicts'] and now+timedelta(minutes=2)<=datetime.fromisoformat(v['ticks'][0])<=first+timedelta(minutes=30)]
 (R/'schedule-diagnostic.json').write_text(json.dumps({'unknown':raw['unknown'],'options':opts,'now':now.isoformat(),'first':first.isoformat()},ensure_ascii=False,indent=2))
 assert not raw['unknown'],'Unknown schedules';assert valid,'No cadence-compatible conflict-free slot'
 choice=assess(m['minutes'][0]) if post else min(valid,key=lambda v:(v['baseline_hits'],v['minutes']))
 assert choice['ticks'] and not choice['operational_conflicts'] and datetime.fromisoformat(choice['ticks'][0])<=first+timedelta(minutes=30)
 result={'pass':True,'generated_at':now.isoformat(),'horizon':raw['horizon'],'selection':choice,'unknown':raw['unknown'],'resource_review':{'Meta':'GET only; v26 common quota/throttle; no Meta writer lease','SB':'Exact authorized publisher, customer/campaign/date projection; read-only report and delay endpoints; distinct source files','browser':False,'lock':str(R/'run.lock'),'timeout_seconds':165,'scheduler_script_timeout':'must exceed wrapper165s','baseline_exception':'Independent infra locks/states; no shared report writer; bounded HTTP collection','custom_schedulers':'Existing landing timers inventoried, own observer state; no campaign writes; no other producer changed'}}
 suffix='after' if post else 'before';(R/('global-schedule-'+suffix+'.json')).write_text(json.dumps(raw,ensure_ascii=False,indent=2));(R/('schedule-'+suffix+'.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2))
 if not post:
  if m.get('scheduler_job_id'):
   assert '--reallocate' in sys.argv,'Already bound job: use explicit amendment'
   assert not (R/'schedule-reallocation-before.json').exists(),'Reconcile existing reallocation first'
   (R/'schedule-reallocation-before.json').write_text(json.dumps({'manifest':m,'reason':'Concurrent operational scheduler occupied original minutes; amend only own job preserving initial receipts and expiration'},ensure_ascii=False,indent=2))
  m.update(minutes=choice['minutes'],slots=choice['ticks']);(R/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2))
 print(json.dumps(result,ensure_ascii=False));return result
if __name__=='__main__':audit('--post' in sys.argv)
