#!/usr/bin/env python3
"""Read-only global scheduler inventory and finite schedule validation."""
import runpy,json,argparse,subprocess
from pathlib import Path
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
from croniter import croniter
HOME=Path('/root/.hermes/profiles/ares');ROOT=Path('/root/mgs-agent/data/ares/meta-ads/state/cpr-roi-updates/1575977166632390947');NY=ZoneInfo('America/New_York')
INFRA={'sync-souls.sh','monitor-auto-push.sh','check-pending-reports.sh','monitor-service-restarts.sh','monitor-tool-loops.sh','track-article-cost.sh','monitor-cron-stale-logs.sh','hermes-news-explainer.py','monitor_honcho_billing_watch.py','discord-archive-stale-agent-threads.py','monitor-vps-health.py','alerts-infra-failed-alert-resolver.py','monitor-hermes-memory-capacity.py','monitor_hermes_pending_writes.py','finalize-hermes-structural-write.py','hermes-news-explainer-watchdog.py','sysstat-collect.timer'}
def classify(e):
    uptime=(e['source']=='root' and e['name']=='monitor-mattei-uptime.py' and e.get('schedule')=='* * * * *' and '/root/mgs-agent/data/mattei-uptime-run.lock' in e.get('command','') and '/root/mgs-agent/scripts/monitor-mattei-uptime.py' in e.get('command',''))
    return uptime or e['name'] in INFRA or (e['source']=='/etc/cron.d/sysstat' and 'debian-sa1 1 1' in e.get('command',''))
def exclude(entries,jid):
    def match(e):return e.get('scheduler_path')==str(HOME/'cron/jobs.json') and e.get('job_id')==jid
    removed=[e for e in entries if match(e)]
    assert len(removed)==1
    return [e for e in entries if not match(e)],removed

def review(entries,slots):
    keys={t.strftime('%Y-%m-%d %H:%M') for t in slots};ops=[];base=[]
    for e in entries:
        hits=[t.isoformat() for t in e['ticks'] if t.strftime('%Y-%m-%d %H:%M') in keys]
        if hits:(base if classify(e) else ops).append({'source':e['source'],'job_id':e.get('job_id'),'name':e['name'],'hits':hits})
    return {'operational_conflicts':ops,'baseline_collisions':base,'baseline_count':sum(len(x['hits']) for x in base)}
def sequence(expr,start,count):
    it=croniter(expr,start)
    return [it.get_next(datetime) for _ in range(count)]
def valid_sequence(m,initial):
    slots=[datetime.fromisoformat(x) for x in m['slots']];assert slots
    assert timedelta(0)<slots[0]-initial<=timedelta(minutes=30)
    assert all(b-a==timedelta(minutes=30) for a,b in zip(slots,slots[1:]))
    assert sequence(m['schedule'],datetime.fromisoformat(m['schedule_anchor']),len(slots))==slots
    assert sequence(m['schedule'],slots[-1],1)[0]>=datetime.fromisoformat(m['expires_at'])
    assert len(slots)==m['repeat_count']
    return slots

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--post');ap.add_argument('--reselect',action='store_true');a=ap.parse_args()
    inv=runpy.run_path(str(HOME/'scripts/shein-g004-cpr-roi-20261127-inventory.py'))['inventory']();assert not inv['unknown']
    entries=inv['entries'];removed=[]
    if a.post:entries,removed=exclude(entries,a.post)
    for e in entries:e['baseline']=classify(e)
    hourly=subprocess.run(['run-parts','--test','/etc/cron.hourly'],capture_output=True,text=True,check=True).stdout.splitlines()
    for e in entries:
        if e['source']=='/etc/crontab' and e.get('command','').endswith('/etc/cron.hourly') and not hourly:e['ticks']=[];e['no_op_evidence']='run-parts --test empty'
    m=json.loads((ROOT/'manifest.json').read_text());now=datetime.now(NY);end=datetime.fromisoformat(m['expires_at']);initial=datetime.fromisoformat(json.loads((ROOT/'runs/initial/complete.json').read_text())['observed_at'])
    if not a.post or a.reselect:
        if m.get('slots'):(ROOT/('schedule-previous-'+now.strftime('%H%M%S')+'.json')).write_text(json.dumps(m,indent=2))
        options=[]
        for minute in range(30):
            slots=[];t=now.replace(second=0,microsecond=0)+timedelta(minutes=3)
            while t<end:
                if t.minute%30==minute:slots.append(t)
                t+=timedelta(minutes=1)
            if slots and timedelta(0)<slots[0]-initial<=timedelta(minutes=30):
                options.append({'minute':minute,'slots':[x.isoformat() for x in slots],**review(entries,slots)})
        good=[x for x in options if not x['operational_conflicts']]
        (ROOT/'allocation-diagnostic.json').write_text(json.dumps({'initial':initial.isoformat(),'now':now.isoformat(),'options':options,'unknown':inv['unknown']},ensure_ascii=False,indent=2))
        assert good,'No compatible zero-operational-conflict slot'
        chosen=min(good,key=lambda x:(x['baseline_count'],x['minute']));m.update(slots=chosen['slots'],minutes=[chosen['minute'],chosen['minute']+30],schedule=f"{chosen['minute']},{chosen['minute']+30} * 27 11 *",repeat_count=len(chosen['slots']),schedule_anchor=now.isoformat())
        valid_sequence(m,initial);(ROOT/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2))
    else:
        slots=valid_sequence(m,initial);chosen={'slots':m['slots'],**review(entries,slots)};assert not chosen['operational_conflicts']
        jobs=json.loads((HOME/'cron/jobs.json').read_text());jobs=jobs if isinstance(jobs,list) else jobs['jobs'];job=next(j for j in jobs if j['id']==a.post)
        assert job['enabled'] and job['state']=='scheduled' and job['script']=='shein-g004-cpr-roi-20261127.sh' and job['no_agent'] and job['deliver']=='local' and job['failure_deliver']=='local' and job['timezone']==str(NY)
        assert job['schedule']['expr']==m['schedule'] and datetime.fromisoformat(job['next_run_at'])==datetime.fromisoformat(m['slots'][0])
        assert job['repeat']['times']==m['repeat_count']
        (ROOT/'scheduler-readback.json').write_text(json.dumps(job,ensure_ascii=False,indent=2))
    result={'pass':True,'generated_at':now.isoformat(),'horizon':inv['horizon'],'selection':chosen,'unknown':inv['unknown'],'self_excluded':a.post,'hourly_noop_executables':hourly,'resource_review':{'lock':str(ROOT/'run.lock'),'duration_timeout_seconds':170,'Meta':'GET only, common quota/throttle; no writer lease or mutations','SB':'exact authorized publisher, read-only campaign report and delay, no browser','Discord':'same thread, nonce/intent/exact GET','other_schedulers':'global root/systemd/all Hermes profiles inspected; landing observers independent event-driven services','dense_operational_jobs':'not exempted as baselines','baseline_exception':'independent infrastructure unavoidable; lowest contention compatible with 30-minute first interval'},'entries':[{**e,'ticks':[t.isoformat() for t in e['ticks']]} for e in entries],'timers':inv['timers']}
    (ROOT/('schedule-post.json' if a.post else 'schedule-pre.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2))
    if not (ROOT/'scheduler-backup.json').exists():(ROOT/'scheduler-backup.json').write_bytes((HOME/'cron/jobs.json').read_bytes())
    print(json.dumps({'pass':True,'schedule':m['schedule'],'repeat':m['repeat_count'],'first':m['slots'][0],'last':m['slots'][-1],'conflicts':len(chosen['operational_conflicts']),'baseline_count':chosen['baseline_count'],'self_excluded':a.post}))
if __name__=='__main__':main()
