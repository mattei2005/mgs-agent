#!/usr/bin/env python3
import json
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
P=Path('/root/mgs-agent/work/hourly-revenue-report')
TODAY='2026-09-05'; YESTERDAY='2026-09-04'; CUTOFF=16

def rows(name):
    d=json.loads((P/name).read_text())
    return d if isinstance(d,list) else next((d[k] for k in ('data','rows','result','results') if isinstance(d.get(k),list)),[])
def dec(v): return Decimal(str(v or 0))
def maps(date):
    c=rows(f'{date}-cumulative.json'); i=rows(f'{date}-incremental.json')
    cm={(r['COMPANY'],r['DOMAIN'],int(r['TIME'])):dec(r.get('NET_REVENUE')) for r in c}
    im={(r['COMPANY'],r['DOMAIN'],int(r['TIME'])):dec(r.get('NET_REVENUE')) for r in i}
    return cm,im
ct,it=maps(TODAY); cy,iy=maps(YESTERDAY)
keys=sorted({k[:2] for m in (ct,it,cy,iy) for k in m})
issues=[]
for m_c,m_i,label in ((ct,it,TODAY),(cy,iy,YESTERDAY)):
    for company,domain in keys:
        prev=Decimal(0)
        for h in range(24):
            cur=m_c.get((company,domain,h),prev)
            inc=m_i.get((company,domain,h),Decimal(0))
            if abs((cur-prev)-inc)>Decimal('0.02'):
                issues.append({'date':label,'company':company,'domain':domain,'hour':h,'delta':str((cur-prev)-inc)})
            prev=cur
summary=[]
for company,domain in keys:
    th=ct.get((company,domain,CUTOFF),Decimal(0)); yh=cy.get((company,domain,CUTOFF),Decimal(0))
    summary.append({'company':company,'domain':domain,'today_to_cutoff':float(th),'yesterday_to_cutoff':float(yh),'difference':float(th-yh),'today_hour':float(it.get((company,domain,CUTOFF),0)),'yesterday_hour':float(iy.get((company,domain,CUTOFF),0))})
summary.sort(key=lambda x:(-x['today_to_cutoff'],x['company'],x['domain']))
qt=Decimal('0.01')
out={'cutoff':CUTOFF,'domains':len(keys),'validation_issues':len(issues),'first_issues':issues[:5],'total_today':float(sum((ct.get((c,d,CUTOFF),0) for c,d in keys),Decimal(0)).quantize(qt,rounding=ROUND_HALF_UP)),'total_yesterday':float(sum((cy.get((c,d,CUTOFF),0) for c,d in keys),Decimal(0)).quantize(qt,rounding=ROUND_HALF_UP)),'current_hour_today':float(sum((it.get((c,d,CUTOFF),0) for c,d in keys),Decimal(0)).quantize(qt,rounding=ROUND_HALF_UP)),'current_hour_yesterday':float(sum((iy.get((c,d,CUTOFF),0) for c,d in keys),Decimal(0)).quantize(qt,rounding=ROUND_HALF_UP)),'top10':summary[:10]}
(P/'analysis-summary.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(out,ensure_ascii=False))
