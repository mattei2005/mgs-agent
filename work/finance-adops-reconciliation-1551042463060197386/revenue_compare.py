import json,collections
from decimal import Decimal as D
from pathlib import Path
W=Path(__file__).parent
load=lambda n:json.loads((W/n).read_text())
r=load('revenue-source-reconciliation.json');s=next(x for x in load('dashboard-db.json') if x['id']=='workspace-2026-08');rules=json.loads(Path('/root/mgs-agent/data/finance-gam-revenue-rules.json').read_text())
brands=rules['brand_domains']|{'ducapesfinance':'finance.ducapes.com','dicasfinancas':'dicasfinancas.info'}
names=rules['dashboard_sites']|{'conectageral.com':'Contecta Geral','seuprimeiroempregoam.com':'SPE','wantabrand.com':'Wantabrand US-CC-ES + Wantabrand BR-CAR-BR','finance.wantabrand.com':'Wantabrand Finance','dicasfinancas.info':'DicasFinancas'}
agg=collections.defaultdict(lambda:collections.defaultdict(D))
for label in ['sb1','sb2']:
 for placement,v in r['sb'][label].items():
  brand=placement.removeprefix('pl_digital-trust_').rsplit('_',1)[0]
  domain=brands[brand];name=names[domain]
  if label=='sb2' and brand not in ['creditoparaveiculo','fincgriffin','gamezonead']:continue
  agg[name][label]+=D(v)
for av in r['av']:agg[names[av['domain']]]['av']+=D(av['consolidated'])
agg[names['wantabrand.com']]['m2']=D(r['m2consolidated']['wantabrand,com:']);agg[names['finance.wantabrand.com']]['m2']=D(r['m2consolidated']['finance,wantabrand,com:'])
for seg in s['result']['domain']['segments']:agg[seg['site']]['dash']+=D(seg['gross'])
fx=D(s['overrides']['principal|Agosto 2026|H1'])
out=[]
for name,amount in sorted(agg.items()):
 expected=amount['sb1']/fx+amount['sb2']+amount['av']+amount['m2'];delta=expected-amount['dash']
 out.append({'site':name,**dict(amount),'expected_usd':expected,'delta_usd':delta,'source_currency_note':'SB1 CAD converted with dash H1; SB2 first 794 rows only; AV provisionally USD/gross; M2 USD'})
(W/'revenue-vs-dashboard.json').write_text(json.dumps({'fx_usdcad':fx,'rows':out,'total_expected_usd':sum(x['expected_usd'] for x in out),'total_dash_usd':sum(x['dash'] for x in out),'total_delta_usd':sum(x['delta_usd'] for x in out)},ensure_ascii=False,default=str,indent=2))
for x in out:print(x['site'],*[f'{k}={x[k]:.2f}' for k in ['sb1','sb2','av','m2','dash','expected_usd','delta_usd']])
print('TOTAL',sum(x['expected_usd'] for x in out),sum(x['dash'] for x in out),sum(x['delta_usd'] for x in out))
