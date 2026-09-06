"""Independent manager/payroll/cash delta check; in-memory TEST sites only."""
import sys,pathlib,json
from decimal import Decimal as D
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));import worker
site={'kind':'site','id':'newsite-TEST-manager-proof','name':'TEST manager proof','new':True,'status':'ATIVO','countries':['US'],'partner':'JBF','currency':'USD','invalid_source':'L1'}
a=worker.run({'additions':[{**site,'manager':'nicolas'}]});b=worker.run({'additions':[{**site,'manager':'SEM_COMISSAO'}]})
allocated=next(s for s in a['domain']['site_catalog'] if s['id']==site['id'])
cost=sum(D(s['expenses']) for s in a['domain']['segments'] if s['site']==site['name'])
profit=lambda r:next(D(x['profit']) for x in r['domain']['managers'] if x['manager']=='nicolas' and x['row']==12)
assert abs(profit(a)-profit(b)-cost)<D('.0000001')
fx=D(a['results']['principal|Agosto 2026|F1']['actual'])
for r in (a,b):
 p=profit(r);brl=p*fx
 expected=-(D(3000)/fx) if brl<=D(3000)/D('.07') else -(p*(D('.07') if brl<D(100000) else D('.10')))
 actual=next(D(x['usd']) for x in r['domain']['expenses'] if x['category']=='personnel' and x['manager']=='nicolas')
 assert abs(actual-expected)<D('.0000001')
 assert abs(sum(D(x['usd']) for x in r['domain']['expenses'] if x['category']=='personnel')-D(r['domain']['cash']['personnel']))<D('.0000001')
out={'pass':True,'manager_delta_equals_site_allocation':True,'independent_payroll_formula':True,'cash_personnel_reconciles':True,'production_writes':0}
(ROOT/'private/ui-catalog-1546169687346249728/manager-allocation-evidence.json').write_text(json.dumps(out,indent=2));print(json.dumps(out))
