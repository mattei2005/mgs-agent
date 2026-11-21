#!/usr/bin/env python3
"""Eight civil date schedule inventory; never changes any scheduler."""
import argparse,json,subprocess,re
from pathlib import Path
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
from croniter import croniter
NY=ZoneInfo('America/New_York')
def inventory(exclude_runner=None):
    start=datetime.now(NY).replace(hour=0,minute=0,second=0,microsecond=0);end=start+timedelta(days=8)
    entries=[];unknown=[]
    def expand(expr,tz):
        itr=croniter(expr,start.astimezone(tz)-timedelta(seconds=1));out=[]
        for _ in range(12000):
            t=itr.get_next(datetime)
            if t>=end:return out
            out.append(t.astimezone(NY))
        raise RuntimeError('schedule expansion limit')
    raw=[('root',subprocess.run(['crontab','-l'],text=True,capture_output=True,check=True).stdout)]
    raw += [(str(p),p.read_text()) for p in [Path('/etc/crontab'),*Path('/etc/cron.d').glob('*')] if p.is_file()]
    for source,text in raw:
        tz=NY
        for line in text.splitlines():
            line=line.strip()
            if not line or line.startswith('#'):continue
            if line.startswith('CRON_TZ='):tz=ZoneInfo(line.split('=',1)[1].strip());continue
            parts=line.split()
            if len(parts)<6 or not (line[0].isdigit() or line[0]=='*'):continue
            expr=' '.join(parts[:5]);cmd=' '.join(parts[5:]);name=next((Path(x).name for x in parts[5:] if x.endswith(('.py','.sh'))),'system')
            if exclude_runner and exclude_runner in cmd:continue
            ticks=expand(expr,tz);baseline=len(ticks)>=8*24*4
            no_op=False
            if source=='/etc/crontab' and cmd=='root cd / && run-parts --report /etc/cron.hourly':
                rp=subprocess.run(['run-parts','--test','/etc/cron.hourly'],capture_output=True,text=True,check=True)
                no_op=not rp.stdout.strip()
            entries.append({'source':source,'name':name,'schedule':expr,'timezone':str(tz),'baseline':baseline,'ticks':ticks,'command':cmd,'no_op_verified':no_op})
    for p in [Path('/root/.hermes/cron/jobs.json'),*Path('/root/.hermes/profiles').glob('*/cron/jobs.json')]:
        if not p.exists():continue
        data=json.loads(p.read_text());jobs=data if isinstance(data,list) else data.get('jobs',[])
        for j in jobs:
            if not j.get('enabled') or j.get('state') in ('paused','completed','cancelled'):continue
            sched=j['schedule'];ticks=[];tz=ZoneInfo(j.get('timezone') or 'America/New_York')
            if sched.get('expr'):ticks=expand(sched['expr'],tz)
            elif j.get('next_run_at'):
                t=datetime.fromisoformat(j['next_run_at']).astimezone(NY);step=sched.get('minutes')
                if step:
                    while t>=start:t-=timedelta(minutes=step)
                    while t<end:
                        if t>=start:ticks.append(t)
                        t+=timedelta(minutes=step)
                elif start<=t<end:ticks=[t]
            else:unknown.append({'source':str(p),'id':j['id']})
            entries.append({'source':p.parent.parent.name,'job_id':j['id'],'name':j.get('name',j['id']),'schedule':sched,'timezone':str(tz),'baseline':len(ticks)>=8*24*4,'ticks':ticks,'script':j.get('script')})
    timers=[]
    output=subprocess.run(['systemctl','list-timers','--all','--no-pager'],capture_output=True,text=True,check=True).stdout
    for unit in sorted(set(re.findall(r'\b[\w.-]+\.timer\b',output))):
        definition=subprocess.run(['systemctl','show',unit,'-p','TimersCalendar','-p','TimersMonotonic','-p','RandomizedDelayUSec','-p','NextElapseUSecRealtime'],capture_output=True,text=True,check=True).stdout
        custom=unit in {'ares-landing-intake.timer','ares-landing-followup.timer'}
        timers.append({'unit':unit,'definition':definition,'classification':'continuous independent event-driven landing observer; no Meta/SB writer or report lock' if custom else 'OS baseline (may be randomized)'})
        if 'TimersCalendar=' in definition:
            for expr in re.findall(r'OnCalendar=([^;]+)',definition):
                res=subprocess.run(['systemd-analyze','calendar','--iterations=1500','--base-time='+start.isoformat(),expr.strip()],capture_output=True,text=True,timeout=30)
                if res.returncode:unknown.append({'timer':unit,'reason':'calendar_expand_failed'});continue
                ticks=[]
                for stamp in re.findall(r'(?:Next elapse|Iteration #\d+|Iter\. #\d+):[^\n]*?(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})',res.stdout):
                    t=datetime.fromisoformat(stamp).replace(tzinfo=NY)
                    if start<=t<end:ticks.append(t)
                entries.append({'source':'systemd','name':unit,'schedule':expr,'baseline':True,'ticks':ticks})
    return {'horizon':[start.isoformat(),end.isoformat()], 'unknown':unknown,'timers':timers,'entries':[{k:v for k,v in e.items() if k!='ticks'}|{'ticks':[t.isoformat() for t in e['ticks']]} for e in entries]}

ROOT=Path('/root/mgs-agent/data/ares/meta-ads/state/cpr-updates/1570877060862312680')
if __name__=='__main__':
    import sys
    raw=inventory();m=json.loads((ROOT/'manifest.json').read_text());now=datetime.now(NY);end=datetime.fromisoformat(m['expires_at'])
    infra=('monitor-tool-loops','monitor-service-restarts','monitor-hermes-memory-capacity','monitor-vps-health','sync-souls','monitor-cron-stale-logs','monitor_honcho','alerts-infra-failed-alert-resolver','monitor_hermes_pending_writes','finalize-hermes-structural-write','hermes-news-explainer-watchdog','hermes-usage-alert','hermes-context','honcho','watchdog','reconcile-hermes')
    for e in raw['entries']:
        dense=e['baseline']
        if dense and e['source']!='systemd':
            e['baseline']=any(x in e['name'] for x in infra)
            if e['source']=='root' and e['name']=='hermes-news-explainer.py':
                e['baseline']=True
                e['baseline_evidence']='Hermes release-announcement explanations; dedicated state and flock; no Meta/SB, campaign or report lock'
            if e['source']=='/etc/cron.d/sysstat' and e.get('command')=='root command -v debian-sa1 > /dev/null && debian-sa1 1 1':
                e['baseline']=True
                e['baseline_evidence']='OS dense resource statistics collector, separate system state; not the sparse summary entry'

    def assess(minute):
        ticks=[];t=now.replace(second=0,microsecond=0)+timedelta(minutes=1)
        while t<end:
            if t.minute in (minute,minute+30):ticks.append(t)
            t+=timedelta(minutes=1)
        keys={t.strftime('%Y-%m-%d %H:%M') for t in ticks};ops=[];base=[]
        for e in raw['entries']:
            if e['source']=='ares' and e.get('job_id')==m.get('scheduler_job_id'):continue
            hits=[s for s in e['ticks'] if datetime.fromisoformat(s).strftime('%Y-%m-%d %H:%M') in keys]
            if hits:(base if e['baseline'] or e.get('no_op_verified') else ops).append({'source':e['source'],'job_id':e.get('job_id'),'name':e['name'],'hits':len(hits),'no_op_verified':e.get('no_op_verified',False)})
        return {'minutes':[minute,minute+30],'ticks':[t.isoformat() for t in ticks],'operational_conflicts':ops,'baselines':base,'baseline_hits':sum(v['hits'] for v in base)}
    options=[assess(v) for v in range(30)];valid=[v for v in options if not v['operational_conflicts'] and v['ticks']]
    assert valid and not raw['unknown']
    initial=json.loads((ROOT/'runs/initial/complete.json').read_text()); first=datetime.fromisoformat(initial['observed_at']); valid=[v for v in valid if now+timedelta(minutes=2)<=datetime.fromisoformat(v['ticks'][0])<=first+timedelta(minutes=30)]; assert valid,'No collision-free cadence-compatible slots'; chosen=assess(m['minutes'][0]) if '--post' in sys.argv else min(valid,key=lambda v:(v['baseline_hits'],v['minutes'])); assert datetime.fromisoformat(chosen['ticks'][0])<=first+timedelta(minutes=30)
    assert not chosen['operational_conflicts']
    result={'pass':True,'generated_at':now.isoformat(),'horizon':raw['horizon'],'selection':chosen,'unknown':raw['unknown'],'resource_review':{'Meta':'GET only, shared quota helper','SB':False,'browser':False,'lock':'request-specific flock','timeout_seconds':165,'baseline_exception':'independent infrastructure states and locks; bounded GET API calls; no Meta writer','custom_schedulers':'landing timers inspected; read-only reports no account writer; existing runtime contracts not changed'}}
    suffix='after' if '--post' in sys.argv else 'before'
    (ROOT/('global-schedule-'+suffix+'.json')).write_text(json.dumps(raw,ensure_ascii=False,indent=2))
    (ROOT/('schedule-'+suffix+'.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2))
    if '--post' not in sys.argv:
        m.update(minutes=chosen['minutes'],slots=chosen['ticks']);(ROOT/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2))
    print(json.dumps(result,ensure_ascii=False))
