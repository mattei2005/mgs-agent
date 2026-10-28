import json,re
from pathlib import Path
from decimal import Decimal as D
from collections import defaultdict,Counter
from datetime import date,timedelta
P=Path(__file__).parent
cohort=json.loads((P/'cohort.json').read_text()); sb=json.loads((P/'sb.json').read_text())
def num(x):
 if x is None or isinstance(x,bool):return None
 try:v=D(str(x));return v if v.is_finite() else None
 except:return None
meta={}
for p in P.glob('*-meta.json'):
 data=json.loads(p.read_text());assert data['pagination_complete']
 for r in data['rows']:
  k=(r['campaign_id'],r['date_start']);assert k not in meta;meta[k]=r
sg=defaultdict(list)
for r in sb['rows']:sg[(str(r['CAMPAIGN_ID']),r['DATE'][:10])].append(r)
assert all(len(rr)==len({(r.get('ADGROUP_ID'),r.get('UTM_ADGROUP')) for r in rr}) for rr in sg.values()),'duplicated adgroup'
def sums(rr,k):
 vals=[num(r.get(k)) for r in rr]
 return sum(vals,D(0)) if vals and all(v is not None for v in vals) else None
start=date(2026,10,14);dates=[(start+timedelta(days=i)).isoformat() for i in range(14)]
records=[]
for c in cohort:
 for day in dates:
  cid=c['campaign_id'];m=meta.get((cid,day));rr=sg.get((cid,day),[])
  spend=num(m.get('spend')) if m else D(0);rev=sums(rr,'NET_REVENUE');inv=sums(rr,'INVESTIMENT')
  if spend>0:assert rev is not None,('missing revenue',cid,day)
  roi=100*(rev-spend)/spend if spend>0 and rev is not None else None
  records.append({'campaign_id':cid,'account_id':c['account_id'],'manager':c['manager'],'date':day,'spend':spend,'revenue':rev,'investment_sb':inv,'roi':roi,'sessions':sums(rr,'SESSIONS'),'impressions':num(m.get('impressions')) if m else D(0),'link_clicks':num(m.get('inline_link_clicks')) if m else D(0),'cdp':sums(rr,'CDP_IMPRESSIONS'),'gam':sums(rr,'GAM_CODE_SERVED_COUNT')})
byc=defaultdict(list)
for r in records:byc[r['campaign_id']].append(r)
def agg(rows):
 valid=[r for r in rows if r['spend']>0 and r['roi'] is not None]
 spend=sum((r['spend'] for r in valid),D(0));rev=sum((r['revenue'] for r in valid),D(0))
 roi=100*(rev-spend)/spend if spend else None
 def sumv(k):return sum((r[k] for r in valid),D(0)) if all(r[k] is not None for r in valid) else None
 return {'n':len(valid),'spend':spend,'revenue':rev,'profit':rev-spend,'roi':roi,'pos':sum(r['roi']>0 for r in valid),'above25':sum(r['roi']>25 for r in valid),'sessions':sumv('sessions'),'impressions':sumv('impressions'),'link_clicks':sumv('link_clicks'),'investment_sb':sumv('investment_sb'),'cdp':sumv('cdp'),'gam':sumv('gam')}
periods={'older':('2026-10-14','2026-10-20'),'baseline':('2026-10-21','2026-10-25'),'recent':('2026-10-26','2026-10-27'),'prior12':('2026-10-14','2026-10-25')}
cs=[]
for c in cohort:
 rr=byc[c['campaign_id']];out=dict(c)
 for label,(lo,hi) in periods.items():out[label]=agg([r for r in rr if lo<=r['date']<=hi])
 out['daily']={r['date']:r['roi'] for r in rr}
 out['number']=re.match(r'^\d+',c['name']).group()
 b=out['baseline'];recent=out['recent']
 if b['n']<3:out['classification']='base_curta'
 elif b['roi']<=0:out['classification']='ja_negativa'
 elif b['roi']<=25:out['classification']='ja_margem_baixa'
 elif b['above25']>b['n']/2 and recent['roi']<b['roi']:out['classification']='queda_recente_base_consistente'
 else:out['classification']='base_positiva_oscilante'
 cs.append(out)
def fmt(v):return 'n/d' if v is None else f'{v:.1f}'
print('COUNTS',dict(Counter(c['classification'] for c in cs)))
for day in dates:
 a=agg([r for r in records if r['date']==day]);print('DAY',day,'ROI',fmt(a['roi']),'spend',fmt(a['spend']),'revenue',fmt(a['revenue']),'campaigns',a['n'],'positive',a['pos'],'above25',a['above25'])
for label,(lo,hi) in periods.items():print('PERIOD',label,agg([r for r in records if lo<=r['date']<=hi]))
for manager in dict.fromkeys(c['manager'] for c in cs):
 cc=[c for c in cs if c['manager']==manager];ids={c['campaign_id'] for c in cc}
 print('MANAGER',manager,len(cc),dict(Counter(c['classification'] for c in cc)))
 for label,(lo,hi) in periods.items():print(' ',label,fmt(agg([r for r in records if r['campaign_id'] in ids and lo<=r['date']<=hi])['roi']))
 for c in cc:print(' CAMP',c['number'],c['classification'],'old',fmt(c['older']['roi']),'base',fmt(c['baseline']['roi']),c['baseline']['n'],c['baseline']['above25'],'recent',fmt(c['recent']['roi']),'26',fmt(c['daily']['2026-10-26']),'27',fmt(c['daily']['2026-10-27']))
assert len(cs)==51 and len(records)==714
out={'date':'2026-10-27','cohort':51,'counts':dict(Counter(c['classification'] for c in cs)),'campaigns':cs,'daily_records':records,'periods':{l:agg([r for r in records if lo<=r['date']<=hi]) for l,(lo,hi) in periods.items()},'daily':{d:agg([r for r in records if r['date']==d]) for d in dates}}
(P/'analysis.json').write_text(json.dumps(out,ensure_ascii=False,indent=2,default=str));(P/'analysis.json').chmod(0o600)
print('DELAY',json.loads((P/'delay.json').read_text()))
