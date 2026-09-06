"""JSON stdin/stdout worker; no credentials, no source writes, no network."""
import sys,json,pathlib,collections
from calc import export,json_default,numeric,num
from expenses import migrate_expenses,compensation
from domain import project,daily,fx_convert,portfolio,project_month
from ui_model import build_model,prepare_inputs,apply_expense_changes
from site_catalog import prepare as prepare_catalog,apply_catalog,account_debits
from periods import prepare as prepare_period,info as period_info
root=pathlib.Path(__file__).parent

def run(payload):
 data=json.loads((root/'private/source.json').read_text())
 model_path=root/'private/ui-model.json'
 model=json.loads(model_path.read_text()) if model_path.exists() else build_model(data)
 overrides=dict(payload.get('overrides',{}));period=payload.get('period','2026-08');start,days=period_info(period)
 for key in model['inputs']:
  if key in overrides:overrides[key]=num(overrides[key])
 data=prepare_inputs(data,overrides,model)
 data=prepare_period(data,model,period,overrides,payload.get('as_of'))
 data,sites,native_catalog=prepare_catalog(data,overrides,payload.get('additions',[]),payload.get('as_of'))
 w,r=export(data,overrides,payload.get('as_of'))
 domain=project(data,w);new=[];expense=migrate_expenses(w)
 domain['expenses']=expense['rows'];domain['summary']['expense_checks']=expense['summary']['checks'];domain['summary']['expense_failures']=expense['summary']['failures']
 domain['cash']=portfolio(domain['facts'],expense['totals']['company'],expense['totals']['personnel'],w.get('principal','Agosto 2026','F1'))
 debits=account_debits(payload.get('additions',[]),w)
 for a in payload.get('additions',[]):
  if a.get('kind') in ('expense','rate','site','account_spend'):continue
  if not a['date'].startswith(period+'-') or not 1<=int(a['date'][-2:])<=days:raise ValueError('Data fora do mês ou inexistente')
  registered=next((s for s in sites if s.get('new') and s['name']==a['site']),None)
  quotes={'USDBRL':w.get('principal','Agosto 2026','F1'),'USDCAD':w.get('principal','Agosto 2026','H1'),'GBPUSD':w.get('principal','Agosto 2026','I1')} if registered else a['quotes']
  invalid=w.get('principal','Agosto 2026',registered['invalid_source']) if registered else a['invalid_rate'];share=w.get('principal','Agosto 2026','EW82' if registered['partner']=='M2' else 'D1') if registered else a['share_rate'];tax=w.get('principal','Agosto 2026','C1') if registered else a['tax_rate']
  gross=fx_convert(a['gross'],a['currency'],quotes);v=daily(gross,-abs(num(a['spend']))-debits.get(a['id'],num(0)),invalid,share,tax)
  new.append({'id':a['id'],'segment':a['site'],'site':a['site'],'partner':a['partner'],'manager':a['manager'],'status':'CENARIO','country':a['country'],'date':a['date'],**v,'source':{},'invalid_rate':invalid,'share_rate':share,'tax_rate':tax,'native_addition':True})
 valid_facts={f['id']:f for f in domain['facts']+new}
 for a in payload.get('additions',[]):
  if a.get('kind')=='account_spend' and (a['fact_id'] not in valid_facts or a['date']!=valid_facts[a['fact_id']]['date']):raise ValueError('Conta sem vínculo de dia válido neste período')
 domain['facts'].extend(new)
 newcost=apply_catalog(domain,sites,w);domain['allocation']['native']=native_catalog
 if new or newcost:
  fx=w.get('principal','Agosto 2026','F1');personnel=domain['cash']['personnel']
  for manager in data['manager_mapping']:
   extras=[f for f in new+newcost if f['manager']==manager]
   if not extras:continue
   delta=sum((num(f['profit']) for f in extras),num(0));invalid_delta=sum((num(f['invalid']) for f in extras),num(0))
   projected=project_month(num(w.get(manager,'Agosto 2026','D12'))+delta,period+'-01',w.as_of.isoformat())
   for cost in domain['expenses']:
    if cost['manager']==manager:
     updated=compensation(projected,fx);personnel+=updated-cost['usd'];cost.update(usd=updated,brl=updated*num(fx))
   for site in sorted({f['site'] for f in extras}):
    contribution=sum((num(f['profit']) for f in extras if f['site']==site),num(0));iv=sum((num(f['invalid']) for f in extras if f['site']==site),num(0))
    match=next((m for m in domain['managers'] if m['manager']==manager and m['row']<12 and ''.join(c for c in m['label'].lower() if c.isalnum())==''.join(c for c in site.lower() if c.isalnum())),None)
    if match:match.update(profit=num(match['profit'])+contribution,invalid=num(match['invalid'])+iv)
    else:domain['managers'].append({'manager':manager,'label':site,'row':0,'profit':contribution,'invalid':iv,'commission7':contribution*num('.07'),'commission10':contribution*num('.10')})
   for row in domain['managers']:
    if row['manager']!=manager or row['row'] not in (12,14):continue
    row['profit']=num(row['profit'])+(delta if row['row']==12 else num(project_month(delta,period+'-01',w.as_of.isoformat())))
    row['invalid']=num(row['invalid'])+invalid_delta;row['commission7']=num(row['profit'])*num('.07');row['commission10']=num(row['profit'])*num('.10')
  domain['cash']=portfolio(domain['facts'],domain['cash']['company_expenses'],personnel,fx)
 changes=[a for a in payload.get('additions',[]) if a.get('kind')=='expense']
 if changes:
  fx=w.get('principal','Agosto 2026','F1')
  domain['expenses']=apply_expense_changes(domain['expenses'],changes,fx)
  totals={k:sum((num(x['usd']) for x in domain['expenses'] if x['category']==k),num(0)) for k in ['company','personnel']}
  domain['cash']=portfolio(domain['facts'],totals['company'],totals['personnel'],fx)
 elapsed=min(days,max(0,(w.as_of-start).days));cash=domain['cash']
 estimate=(sum((num(f['profit']) for f in domain['facts']),num(0))*days/elapsed+num(cash['company_expenses'])+num(cash['personnel']))/2 if elapsed else None
 domain['projection']={'period':period,'days':days,'elapsed':elapsed,'state':'planned' if w.as_of<start else 'closed' if elapsed==days else 'in_progress','half_usd':estimate,'half_brl':estimate*num(w.get('principal','Agosto 2026','F1')) if estimate is not None else None}
 results={x['id']:{'actual':x['actual'],'status':x['status'],**({'error':x['error']} if 'error' in x else {})} for x in r['rows']}
 formula_count=sum(x['kind'] in ('formula','external_quote') for x in data['cells'])
 formula_pass=sum(x['kind']=='formula' and x['status']=='pass' for x in r['rows'])
 summary={'counts':r['counts'],'formulas_total':formula_count,'formulas_recalculated':formula_pass,'frozen_quotes':sum(x['kind']=='external_quote' for x in r['rows']),'historical_boundaries':sum(x['kind']=='historical_boundary' for x in r['rows']),'as_of':r['as_of'],'period':period,'domain':domain['summary'],'native_additions':len(new),'status':'PARITY_PASS' if not r['issues'] and not domain['summary']['daily_failures'] and not domain['summary']['cash_failures'] and not domain['summary']['expense_failures'] and not new else 'SCENARIO_CHANGED','production_ready':False}
 if changes or native_catalog:summary['status']='SCENARIO_CHANGED'
 # All expected values remain in the immutable imported evidence only.
 domain.pop('checks');domain.pop('bindings');domain.pop('cash_checks')
 return {'engine_revision':'finance-homologation-3','summary':summary,'domain':domain,'results':results,'issues':r['issues'],'boundaries':data['boundaries']}
if __name__=='__main__':
 result=run(json.load(sys.stdin));sys.stdout.write(json.dumps(result,ensure_ascii=False,default=json_default))
