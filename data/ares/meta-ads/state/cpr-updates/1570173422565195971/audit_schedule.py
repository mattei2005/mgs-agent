#!/usr/bin/env python3
"""Read-only eight-day global inventory and request-scoped finite selection."""
import ast, json, argparse, shutil
from pathlib import Path
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from croniter import croniter
ROOT=Path('/root/mgs-agent/data/ares/meta-ads/state/cpr-updates/1570173422565195971')
NY=ZoneInfo('America/New_York')
INFRA={'sync-souls.sh','monitor-auto-push.sh','check-pending-reports.sh','monitor-service-restarts.sh','monitor-tool-loops.sh','track-article-cost.sh','monitor-cron-stale-logs.sh','hermes-news-explainer.py','monitor_honcho_billing_watch.py','discord-archive-stale-agent-threads.py','monitor-vps-health.py','alerts-infra-failed-alert-resolver.py','monitor_hermes_pending_writes.py','finalize-hermes-structural-write.py','monitor-hermes-memory-capacity.py','hermes-news-explainer-watchdog.py','meta-app-roles-watch','b013-dtr-link-watch'}
def inventory():
    p=Path('/root/.hermes/profiles/ares/scripts/shein-daily-schedule-audit.py')
    source=p.read_text()
    source=source.replace("'script':j.get('script')}","'script':j.get('script'),'job_id':j['id']}")
    source=source.replace(r'Iter\. #\d+',r'Iter\. #\s*\d+')
    tree=ast.parse(source)
    fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='inventory')
    fn.body=fn.body[:next(i for i,n in enumerate(fn.body) if isinstance(n,ast.Assign) and any(isinstance(a,ast.Name) and a.id=='candidates' for a in n.targets))]
    fn.body.append(ast.parse("return {'entries':entries,'unknown':unknown,'timers':timers,'horizon':[start.isoformat(),end.isoformat()]}").body[0])
    tree.body=[n for n in tree.body if isinstance(n,(ast.Import,ast.ImportFrom))]+[fn]
    ns={'NY':NY};exec(compile(ast.fix_missing_locations(tree),str(p),'exec'),ns)
    result=ns['inventory']()
    for e in result['entries']:
        if e['source']=='systemd': e['baseline']=True
        elif e['source']=='/etc/cron.d/sysstat':e['baseline']=True
        else:e['baseline']=e['name'] in INFRA and len(e['ticks'])>=8*24*4
    return result

def audit(post=False):
    m=json.loads((ROOT/'manifest.json').read_text());r=inventory()
    own=m.get('scheduler_job_id') if post else None
    entries=[e for e in r['entries'] if not (e.get('job_id')==own and e['source']=='ares')]
    now=datetime.now(NY);expires=datetime.fromisoformat(m['expires_at'])
    initial=json.loads((ROOT/'runs/initial/complete.json').read_text())
    initial_at=datetime.fromisoformat(initial['observed_at'])
    candidates=[]
    for minute in range(30):
        slots=[];t=now.replace(second=0,microsecond=0)+timedelta(minutes=2)
        while t<expires:
            if t.minute%30==minute:slots.append(t)
            t+=timedelta(minutes=1)
        if not slots or not (0<(slots[0]-initial_at).total_seconds()<=1800):continue
        keys={s.strftime('%Y-%m-%d %H:%M') for s in slots};ops=[];base=[]
        for e in entries:
            hits=[t.isoformat() for t in e['ticks'] if t.strftime('%Y-%m-%d %H:%M') in keys]
            if hits:(base if e['baseline'] else ops).append({'source':e['source'],'name':e['name'],'hits':hits})
        candidates.append({'minute':minute,'minutes':[minute,minute+30],'slots':[t.isoformat() for t in slots],'operational_conflicts':ops,'baseline_collisions':base,'baseline_count':sum(len(e['hits']) for e in base)})
    viable=[x for x in candidates if not x['operational_conflicts']]
    assert viable and not r['unknown'],'Unresolved global schedule conflict'
    best=min(viable,key=lambda x:(x['baseline_count'],x['slots'][0]))
    if post:
        selected=next(x for x in candidates if x['minutes']==m['minutes'])
        assert not selected['operational_conflicts']
        assert selected['slots']==m['slots'],'Scheduler window changed during preparation'
    else:
        selected=best;m.update(minutes=selected['minutes'],slots=selected['slots'])
        m['cron_expr']=','.join(map(str,m['minutes']))+' '+str(datetime.fromisoformat(m['slots'][0]).hour)+'-23 11 11 *'
        (ROOT/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2))
    itr=croniter(m['cron_expr'],now)
    ticks=[itr.get_next(datetime).isoformat() for _ in m['slots']]
    assert ticks==m['slots'],'Physical/logical sequence mismatch'
    assert itr.get_next(datetime)>=expires
    result={'pass':True,'generated_at':now.isoformat(),'horizon':r['horizon'],'unknown':r['unknown'],'selection':selected,'self_excluded_job_id':own,'resource_review':{'lock':str(ROOT/'run.lock'),'account_id':m['account_id'],'Meta':'GET only through common throttle, quota and account guard; no campaign write or browser','SB':'not queried','timeout_seconds':165,'baselines':'independent infra paths/locks; no shared browser or report state','other_schedulers_unchanged':True},'timers':r['timers'],'entries':r['entries']}
    target=ROOT/('schedule-post.json' if post else 'schedule-pre.json');target.write_text(json.dumps(result,ensure_ascii=False,indent=2,default=lambda x:x.isoformat()))
    print(json.dumps({'pass':True,'minutes':m['minutes'],'first':m['slots'][0],'last':m['slots'][-1],'count':len(m['slots']),'operational_conflicts':len(selected['operational_conflicts']),'baseline_count':selected['baseline_count'],'unknown':r['unknown'],'job_id_excluded':own}))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--post',action='store_true');a=p.parse_args();audit(a.post)
