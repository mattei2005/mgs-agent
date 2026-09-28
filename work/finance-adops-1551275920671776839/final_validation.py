import sys,json,collections,hashlib,datetime,shlex
from decimal import Decimal as D
from pathlib import Path
sys.path.insert(0,'/root/mgs-agent/scripts');from mgs_google_workspace_auth import load_env;load_env()
sys.path.insert(0,'/root/mgs-agent/apps/finance-system/deploy');from runcloud_ops import ssh
W=Path(__file__).parent;S=W/'source-update-1551279009415958700'
q="SELECT json_agg(t) FROM (SELECT * FROM scenarios WHERE id IN ('workspace-2026-08','master-ad-accounts'))t"
raw=ssh('sudo -u mgs_pg env LD_LIBRARY_PATH=/opt/mgs-postgresql18/usr/lib/x86_64-linux-gnu /opt/mgs-postgresql18/usr/lib/postgresql/18/bin/psql -h /run/mgs-postgresql18 -d mgs_finance -At -c '+shlex.quote(q));d=json.loads(raw);(W/'dashboard-after.json').write_text(raw)
s=next(x for x in d if x['id']=='workspace-2026-08');p=json.load(open(W/'plan.json'));before=next(x for x in json.load(open(W/'dashboard-db.json')) if x['id']=='workspace-2026-08')
assert s['revision']==392
rows=lambda sid:json.load(open(S/f'{sid}-UNFORMATTED_VALUE.json'))['values']
g=collections.defaultdict(D)
for r in rows(1938914193)[1:]:
 if len(r)>6 and r[0]!='Total':g[r[1]]+=D(str(r[6]))
av=[]
for r in rows(1839542079)[1:]:
 if len(r)>2 and r[0]:
  dom=r[1];detail=g.get(dom)
  if dom.startswith('openzed.com '):
   tag=dom.split()[-1];detail=sum(D(str(x[6])) for x in rows(1938914193)[1:] if len(x)>6 and x[1]=='openzed.com' and x[5].startswith(tag))
  av.append({'domain':dom,'consolidated':str(D(str(r[2]))),'detailed':None if detail is None else str(detail),'delta':None if detail is None else str(D(str(r[2]))-detail)})
by_site=collections.defaultdict(D)
for f in s['result']['domain']['facts']:by_site[f['site']]+=D(str(f['gross'] or 0))
amounts=collections.defaultdict(D)
for x in p['gross_checks']+p['residual_entries']:
 amounts[(x['site'],x['currency'])]+=D(str(x.get('expected',x.get('gross'))))
fx=D(s['result']['results']['principal|Agosto 2026|H1']['actual'])
for site in p['gross_sites']+sorted({x['site'] for x in p['residual_entries']}):
 expected=amounts[(site,'CAD')]/fx+amounts[(site,'USD')];assert abs(by_site[site]-expected)<D('0.000000001'),site
spendchanges=[x for x in p['changes'].values() if x['reason'].startswith(('Facebook','Google'))]
summary={'pass':True,'revision':s['revision'],'account_revision':next(x for x in d if x['id']=='master-ad-accounts')['revision'],'fb_accounts':48,'google_accounts':2,'spend_input_changes':len(spendchanges),'gross_input_changes':len(p['changes'])-len(spendchanges),'source_complete_revenue_sites':len(p['gross_sites'])+len({x['site'] for x in p['residual_entries']}),'source_complete_revenue_totals':[{ 'site':site,'currency':cur,'amount':str(amount)} for (site,cur),amount in amounts.items() if amount], 'av_comparison':av,'av_consolidated_total':str(sum(D(x['consolidated']) for x in av)),'av_detailed_total':str(sum(g.values())),'fb_usd':'286368.15','google_brl':'71174.24','spend_consolidated_usd':str(-D(s['result']['domain']['cash']['spend'])),'partial_gross_usd':str(D(s['result']['domain']['cash']['gross'])),'new_topfeed_rows':sum(x[1]=='finanzas.topfeed.fun' for x in rows(1938914193)[1:] if len(x)>1)}
(W/'final-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in summary.items() if k not in ['source_complete_revenue_totals','av_comparison']},ensure_ascii=False))
print('SERVICES',ssh('systemctl is-active mgs-postgresql18 mgs-finance-dash mgs-finance-dash.socket').strip().splitlines())
