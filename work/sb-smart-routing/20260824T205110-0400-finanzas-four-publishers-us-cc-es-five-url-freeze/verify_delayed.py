#!/usr/bin/env python3
import datetime as dt
import hashlib
import json
from pathlib import Path
from zoneinfo import ZoneInfo

RUN=Path('/root/mgs-agent/work/sb-smart-routing/20260824T205110-0400-finanzas-four-publishers-us-cc-es-five-url-freeze')
manifest=json.loads((RUN/'01-manifest.json').read_text())

def parse_routes(value):
    return json.loads(value) if isinstance(value,str) else value

def core(route):
    return {
        'route':str(route.get('route') or '').strip(),
        'utm_content':str(route.get('utm_content') or '').strip(),
        'url':str(route.get('url') or '').strip().rstrip('/'),
        'jbf_operation':str(route.get('jbf_operation') or '').strip(),
        'healthy':bool(route.get('healthy',True)),
        'freeze':bool(route.get('freeze',False)),
        'freeze_sessions':int(route.get('freeze_sessions') or 0),
    }

result={'checked_at_et':dt.datetime.now(ZoneInfo('America/New_York')).isoformat(timespec='seconds'),'publishers':{},'errors':[]}
for slug,publisher in manifest['publishers'].items():
    current=json.loads(Path(f'/tmp/sb-{slug}-list/backup/before-target-pools.json').read_text())
    by_id={int(pool['ID']):pool for pool in current}
    rows=[]
    for plan in publisher['plans']:
        pool=by_id.get(int(plan['id']))
        if not pool:
            result['errors'].append(f"{slug}: pool {plan['id']} missing")
            continue
        actual=[core(route) for route in parse_routes(pool['ROUTES'])]
        expected=[core(route) for route in plan['routes']]
        errors=[]
        if actual!=expected: errors.append('route payload mismatch')
        if any(not route['freeze'] or route['freeze_sessions']!=0 for route in actual): errors.append('freeze mismatch')
        rows.append({'id':plan['id'],'name':plan['name'],'family':plan['family'],'routes':len(actual),'exact':not errors,'errors':errors})
        result['errors'].extend(f"{slug}/{plan['id']}: {error}" for error in errors)
    all_routes=[route for row in publisher['plans'] for route in row['routes']]
    result['publishers'][slug]={
        'pools':rows,
        'pool_count':len(rows),
        'routes':sum(row['routes'] for row in rows),
        'frozen':sum(1 for route in all_routes if route.get('freeze') and int(route.get('freeze_sessions') or 0)==0),
        'exact':all(row['exact'] for row in rows),
    }
result['status']='PASS' if not result['errors'] else 'FAIL'
raw=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
(RUN/'96-delayed-frozen-readback.json').write_text(raw)
print(json.dumps({'status':result['status'],'errors':result['errors'],'publishers':{slug:{k:value[k] for k in ('pool_count','routes','frozen','exact')} for slug,value in result['publishers'].items()},'sha256':hashlib.sha256(raw.encode()).hexdigest()},ensure_ascii=False,indent=2))
raise SystemExit(0 if result['status']=='PASS' else 1)
