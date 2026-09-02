#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import json
import os
import re
import subprocess
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path('/root/mgs-agent')
OUT = Path(os.environ.get('CRON_AUDIT_OUT', str(ROOT / 'data/ares/audits/eggbev/completeness-r5-20260902/cron-collision-r5.json')))
NY = ZoneInfo('America/New_York')
SP = ZoneInfo('America/Sao_Paulo')
UTC = dt.timezone.utc
START = dt.datetime(2026, 9, 2, 0, 0, tzinfo=NY)
END = START + dt.timedelta(days=8)


def field_values(field: str, minimum: int, maximum: int) -> set[int]:
    values: set[int] = set()
    for token in field.split(','):
        token = token.strip()
        if not token:
            continue
        step = 1
        if '/' in token:
            token, raw_step = token.split('/', 1)
            step = int(raw_step)
        if token == '*':
            start, end = minimum, maximum
        elif '-' in token:
            start_s, end_s = token.split('-', 1)
            start, end = int(start_s), int(end_s)
        else:
            start = end = int(token)
        values.update(range(start, end + 1, step))
    return {v for v in values if minimum <= v <= maximum}


def cron_match(expr: str, local: dt.datetime) -> bool:
    parts = expr.split()
    if len(parts) != 5:
        return False
    minute, hour, dom, month, dow = parts
    if local.minute not in field_values(minute, 0, 59): return False
    if local.hour not in field_values(hour, 0, 23): return False
    if local.day not in field_values(dom, 1, 31): return False
    if local.month not in field_values(month, 1, 12): return False
    py_dow = (local.weekday() + 1) % 7
    dows = field_values(dow.replace('7', '0'), 0, 6)
    return py_dow in dows


def resource(name: str, command: str) -> list[str]:
    text = (name + ' ' + command).lower()
    tags=[]
    if any(x in text for x in ['smart', 'sb-', 'messenger', 'broadcast']): tags.append('smart_bidding')
    if any(x in text for x in ['meta', 'roas', 'campaign', 'creative-cut', 'first-delivery']): tags.append('meta_api')
    if any(x in text for x in ['backup', 'restore']): tags.append('backup_io')
    if 'yoast' in text: tags.append('wordpress_ssh')
    if any(x in text for x in ['discord', 'thread']): tags.append('discord_api')
    if not tags: tags.append('local_or_other')
    return sorted(set(tags))


def dense(expr: str) -> bool:
    parts=expr.split()
    if len(parts)!=5: return False
    mins=field_values(parts[0],0,59)
    hours=field_values(parts[1],0,23)
    return len(mins) >= 4 and len(hours) >= 20

jobs=[]
# Root crontab with CRON_TZ state.
crontab_file=os.environ.get('CRONTAB_AUDIT_FILE')
raw=Path(crontab_file).read_text(encoding='utf-8') if crontab_file else subprocess.run(['crontab','-l'],text=True,capture_output=True,check=True).stdout
current_tz=NY
for raw_line in raw.splitlines():
    line=raw_line.strip()
    if not line or line.startswith('#'): continue
    if line.startswith('CRON_TZ='):
        current_tz=ZoneInfo(line.split('=',1)[1].strip())
        continue
    parts=line.split()
    if len(parts)<6: continue
    expr=' '.join(parts[:5]); command=' '.join(parts[5:])
    name='root:'+Path(next((p for p in re.findall(r'/[^\s]+', command) if '/scripts/' in p), command.split()[0])).name
    jobs.append({'source':'root','id':f'root-{len(jobs)+1}','name':name,'expr':expr,'timezone':str(current_tz),'command':command,'dense_baseline':dense(expr),'resources':resource(name,command)})

# Hermes per-profile jobs.
for profile in ['zeus','atena','ares']:
    path=Path(f'/root/.hermes/profiles/{profile}/cron/jobs.json')
    if not path.exists(): continue
    data=json.loads(path.read_text())
    rows=data.get('jobs',data if isinstance(data,list) else [])
    for row in rows:
        if row.get('enabled') is not True or row.get('state')!='scheduled': continue
        sched=row.get('schedule') or {}
        if isinstance(sched,dict) and sched.get('kind')=='cron':
            expr=str(sched.get('expr') or '')
        else:
            continue
        name=str(row.get('name') or row.get('id'))
        cmd=str(row.get('script') or '')
        jobs.append({'source':f'hermes_{profile}','id':str(row.get('id')),'name':name,'expr':expr,'timezone':'America/New_York','command':cmd,'dense_baseline':dense(expr),'resources':resource(name,cmd)})

# Static minute expansion in UTC.
occ={j['id']:set() for j in jobs}
t=START.astimezone(UTC)
while t < END.astimezone(UTC):
    for j in jobs:
        local=t.astimezone(ZoneInfo(j['timezone']))
        if cron_match(j['expr'],local): occ[j['id']].add(t)
    t += dt.timedelta(minutes=1)

# Identify exact target jobs.
target_ids=[]
for j in jobs:
    txt=(j['name']+' '+j['command']).lower()
    if 'eggbev corte e roas' in txt or 'eggbev-roas-cycle-controlled.sh' in txt:
        j['target']='roas'; target_ids.append(j['id'])
    elif 'eggbev limite de leads' in txt or 'eggbev-page-lead-guardrail.sh' in txt:
        j['target']='leads'; target_ids.append(j['id'])
    elif 'eggbev-page-restriction-guardrail.sh' in txt:
        j['target']='dtr_restriction'; j['physical_stagger_seconds']=30; target_ids.append(j['id'])

by_id={j['id']:j for j in jobs}
overlaps=[]
for tid in target_ids:
    target=by_id[tid]
    for oid in occ:
        if oid==tid: continue
        same=sorted(occ[tid] & occ[oid])
        if not same: continue
        other=by_id[oid]
        shared=sorted(set(target['resources']) & set(other['resources']))
        overlaps.append({
            'target':target['target'],
            'target_id':tid,
            'other_id':oid,
            'other_source':other['source'],
            'other_name':other['name'],
            'other_expr':other['expr'],
            'other_timezone':other['timezone'],
            'occurrences_8d':len(same),
            'samples_et':[x.astimezone(NY).isoformat() for x in same[:8]],
            'other_dense_baseline':other['dense_baseline'],
            'target_stagger_seconds':target.get('physical_stagger_seconds',0),
            'target_resources':target['resources'],
            'other_resources':other['resources'],
            'shared_resource_tags':shared,
        })

payload={
 'audit_id':'ARES-EGGBEV-CRON-COLLISION-R5-20260902',
 'window_et':[START.isoformat(),END.isoformat()],
 'jobs_static_total':len(jobs),
 'targets':[by_id[x] for x in target_ids],
 'overlaps':sorted(overlaps,key=lambda x:(x['target'],x['other_dense_baseline'],x['other_source'],x['other_name'])),
 'systemd_note':'systemd timers were inventoried separately; this expansion covers static root/Hermes cron expressions. Dynamic interval jobs require duration/resource review but have no stable cron residue.',
}
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n')
summary={}
for row in overlaps:
 summary.setdefault(row['target'],{'all':0,'non_dense':0,'shared_resource':0})
 summary[row['target']]['all']+=1
 summary[row['target']]['non_dense']+=0 if row['other_dense_baseline'] else 1
 summary[row['target']]['shared_resource']+=1 if row['shared_resource_tags'] else 0
print(json.dumps({'jobs':len(jobs),'targets':len(target_ids),'overlap_pairs':len(overlaps),'summary':summary},ensure_ascii=False))
for row in overlaps:
 if not row['other_dense_baseline'] or row['shared_resource_tags']:
  print(json.dumps(row,ensure_ascii=False))
