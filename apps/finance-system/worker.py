"""JSON stdin/stdout worker; no credentials, no source writes, no network."""
import sys,json,pathlib,collections
from calc import export,json_default,numeric,num
from expenses import migrate_expenses,compensation,apply_payroll_policy
from domain import project,daily,fx_convert,portfolio,project_month
from ui_model import build_model,prepare_inputs,apply_expense_changes
from site_catalog import prepare as prepare_catalog,apply_catalog,account_debits
from account_manager_costs import native_manager_costs
from direct_costs import direct_monthly_costs,direct_daily_costs
from periods import prepare as prepare_period,info as period_info
from financial_cutoff import prepare as prepare_cutoff,materialize_manager_totals
from networks import prepare as prepare_networks,NETWORKS,canonical
from currency_bridge import prepare as prepare_currency
from august_reconciliation import prepare as prepare_august_reconciliation
from gross_pairs import prepare as prepare_gross_pairs, total as pair_total, annotate as annotate_pairs, legacy_origins
root=pathlib.Path(__file__).parent

def validate_monthly_adjustment(a, period):
    if period!='2026-08' or a.get('period')!=period or a.get('date')!=period:
        raise ValueError('Ajuste mensal fora do escopo autorizado')
    if a.get('authority')=='1551358728870035530':
        return
    # Rodolfo1554177164872519692: two bounded closing deltas, not invented daily revenue.
    targets={'CreditoParaVeiculo':('cpv','71824.15'),'GameZoneAd':('gamezone','13653.88')}
    rule=targets.get(a.get('site'))
    if (a.get('authority')!='1554177164872519692' or not rule
        or a.get('id')!='august-rede2-1554177164872519692-'+rule[0]
        or a.get('target_monthly_gross')!=rule[1] or a.get('manager')!='SEM_COMISSAO'
        or a.get('country')!='BR' or a.get('partner')!='SB Rede2' or a.get('currency')!='USD'
        or a.get('source_network')!='SB Rede2' or num(a.get('spend'))!=0
        or not 0<num(a.get('gross'))<20):
        raise ValueError('Ajuste mensal fora do escopo autorizado')

def run(payload):
 data=json.loads((root/'private/source.json').read_text())
 model_path=root/'private/ui-model.json'
 model=json.loads(model_path.read_text()) if model_path.exists() else build_model(data)
 overrides=dict(payload.get('overrides',{}));period=payload.get('period','2026-08');start,days=period_info(period)
 for key in model['inputs']:
  if key in overrides:overrides[key]=num(overrides[key])
 data=prepare_inputs(data,overrides,model)
 data=prepare_period(data,model,period,overrides,payload.get('as_of'))
 data=prepare_august_reconciliation(data,payload.get('additions',[]),period)
 data=prepare_currency(data,payload.get('additions',[]),period)
 data=prepare_networks(data,overrides,payload.get('additions',[]))
 data,actual_as_of,explicit_cutoff=prepare_cutoff(data,payload.get('additions',[]),period,start,days,payload.get('as_of'))
 calculation_as_of=data['as_of'] if explicit_cutoff else payload.get('as_of')
 overrides,gross_pairs,gross_currencies=prepare_gross_pairs(data,overrides,model,payload.get('additions',[]),period,calculation_as_of)
 # Pairs may introduce an override for an originally blank, model-approved leaf.
 data=prepare_inputs(data,overrides,model)
 if explicit_cutoff:overrides.update({key:'' for key in explicit_cutoff['blank_manager_inputs']})
 data,sites,native_catalog=prepare_catalog(data,overrides,payload.get('additions',[]),calculation_as_of)
 if explicit_cutoff:data,overrides=materialize_manager_totals(data,overrides,calculation_as_of)
 w,r=export(data,overrides,calculation_as_of)
 domain=project(data,w);new=[];expense=migrate_expenses(w)
 annotate_pairs(domain['facts'],model,gross_pairs,gross_currencies,w)
 if gross_pairs:domain['legacy_gross_origins']=legacy_origins(domain['facts'],model,gross_pairs,gross_currencies,w)
 domain['expenses']=expense['rows'];domain['summary']['expense_checks']=expense['summary']['checks'];domain['summary']['expense_failures']=expense['summary']['failures']
 domain['cash']=portfolio(domain['facts'],expense['totals']['company'],expense['totals']['personnel'],w.get('principal','Agosto 2026','F1'))
 debits=account_debits(payload.get('additions',[]),w)
 for a in payload.get('additions',[]):
  if a.get('kind') in ('expense','rate','site','account_spend','data_cutoff','reconciliation_policy','gross_pair','direct_monthly_cost','direct_daily_cost','prepaid_credit','sms_usage_receipt'):continue
  monthly=a.get('kind')=='monthly_gross_adjustment'
  if monthly:
   validate_monthly_adjustment(a,period)
  elif not a['date'].startswith(period+'-') or not 1<=int(a['date'][-2:])<=days:raise ValueError('Data fora do mês ou inexistente')
  registered=next((s for s in sites if s['name']==a['site'] and (s.get('new') or s.get('network'))),None)
  quotes={'USDBRL':w.get('principal','Agosto 2026','F1'),'USDCAD':w.get('principal','Agosto 2026','H1'),'GBPUSD':w.get('principal','Agosto 2026','I1')} if registered else a['quotes']
  invalid=w.get('principal','Agosto 2026',registered['invalid_source']) if registered else a['invalid_rate'];share=w.get('principal','Agosto 2026','EW82' if registered['partner']=='M2' else 'D1') if registered else a['share_rate'];tax=w.get('principal','Agosto 2026','C1') if registered else a['tax_rate']
  pair=gross_pairs.get(('entry',a['id']))
  gross=pair_total(pair,quotes['USDCAD']) if pair else fx_convert(a['gross'],a['currency'],quotes);v=daily(gross,-abs(num(a['spend']))-debits.get(a['id'],num(0)),invalid,share,tax)
  new.append({'id':a['id'],'segment':a['site'],'site':a['site'],'partner':registered['partner'] if registered and registered.get('network_binding_explicit') else a['partner'],'manager':a['manager'],'status':'CENARIO','country':a['country'],'date':a['date'],**v,'source':{},'invalid_rate':invalid,'share_rate':share,'tax_rate':tax,'native_addition':True})
  new[-1].update(source_vertical=a.get('source_vertical'),source_manager_tag=a.get('source_manager_tag'),source_import_type=a.get('source_import_type'),revenue_superseded=bool(a.get('revenue_superseded_by')),monthly_closing=monthly)
  if monthly:new[-1]['gross_origins']={'USD':num(a['gross'])}
  if pair:new[-1]['gross_origins']={c:num(pair[k]) for c,k in [('CAD','cad'),('USD','usd')] if pair.get(k) not in ('',None)}
 new.extend(direct_monthly_costs(payload.get('additions',[]),sites,w,period))
 new.extend(direct_daily_costs(payload.get('additions',[]),sites,w,period))
 domain['facts'].extend(new)
 # Catalog day anchors are valid spend targets even before GAM revenue arrives.
 # Materialize them before validation; retain referenced anchors on later intake.
 newcost=apply_catalog(domain,sites,w,debits=debits);domain['allocation']['native']=native_catalog
 valid_facts={f['id']:f for f in domain['facts']}
 for a in payload.get('additions',[]):
  if a.get('kind')=='account_spend' and (a['fact_id'] not in valid_facts or a['date']!=valid_facts[a['fact_id']]['date'] or a.get('site')!=valid_facts[a['fact_id']]['site']):raise ValueError('Conta sem vínculo de dia válido neste período')
 native_costs=native_manager_costs(payload.get('additions',[]),sites,w);domain['native_manager_spend']=native_costs;newcost.extend(native_costs)
 if new or newcost:
  fx=w.get('principal','Agosto 2026','F1');personnel=domain['cash']['personnel']
  for manager in data['manager_mapping']:
   extras=[f for f in new+newcost if f['manager']==manager and (not explicit_cutoff or not f.get('date') or f.get('monthly_closing') or explicit_cutoff['cutoff_date'] and f['date']<=explicit_cutoff['cutoff_date'])]
   if not extras:continue
   delta=sum((num(f['profit']) for f in extras),num(0));invalid_delta=sum((num(f['invalid']) for f in extras),num(0))
   projected=project_month(num(w.get(manager,'Agosto 2026','D12'))+delta,period+'-01',w.as_of.isoformat())
   for cost in domain['expenses']:
    if cost['manager']==manager:
     updated=compensation(projected,fx);personnel+=updated-cost['usd'];cost.update(usd=updated,brl=updated*num(fx))
   def site_identity(value):
    clean=''.join(c for c in value.lower() if c.isalnum())
    return {'wantabrandes':'wantabranduscceswantabrandbrcarbr','wantabranduscces':'wantabranduscceswantabrandbrcarbr','finanzastopfeed':'topfeedfinanzas'}.get(clean,clean)
   for site in sorted({f['site'] for f in extras}):
    contribution=sum((num(f['profit']) for f in extras if f['site']==site),num(0));iv=sum((num(f['invalid']) for f in extras if f['site']==site),num(0))
    match=next((m for m in domain['managers'] if m['manager']==manager and m['row']<12 and site_identity(m['label'])==site_identity(site)),None)
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
  domain['expenses']=apply_expense_changes(domain['expenses'],changes,fx,{'CAD':w.get('principal','Agosto 2026','H1'),'UNITS':w.get('principal','Agosto 2026','G1')})
  domain['expenses']=apply_payroll_policy(domain['expenses'],changes,domain['managers'],fx)
  totals={k:sum((num(x['usd']) for x in domain['expenses'] if x['category']==k),num(0)) for k in ['company','personnel']}
  domain['cash']=portfolio(domain['facts'],totals['company'],totals['personnel'],fx)
 if explicit_cutoff:
  cutoff_date=explicit_cutoff['cutoff_date'];elapsed=explicit_cutoff['elapsed_days'];source=explicit_cutoff['source']
 else:
  elapsed=min(days,max(0,(w.as_of-start).days));cutoff_date=f'{period}-{elapsed:02d}' if elapsed else None;source='legacy_as_of_fallback'
 realized_facts=[f for f in domain['facts'] if cutoff_date and f['date']<=cutoff_date];cash=domain['cash'];fixed_general=num(cash['company_expenses'])*elapsed/days;fixed_staff=num(cash['personnel'])*elapsed/days
 realized={k:sum((num(f.get(k,0)) for f in realized_facts),num(0)) for k in ['gross','invalid','net','tax','spend','direct_expense']};realized['revshare']=realized['net']-realized['gross']-realized['invalid'];realized.update(company_expenses=fixed_general,personnel=fixed_staff,profit=realized['net']+realized['tax']+realized['spend']+realized['direct_expense']+fixed_general+fixed_staff,cutoff_date=cutoff_date,elapsed_days=elapsed,month_days=days,source=source)
 realized['half_usd']=realized['profit']/2;realized['half_brl']=realized['half_usd']*num(w.get('principal','Agosto 2026','F1'));domain['realized']=realized
 operating=sum((num(f['profit']) for f in realized_facts),num(0));estimate=(operating*days/elapsed+num(cash['company_expenses'])+num(cash['personnel']))/2 if elapsed else None
 domain['projection']={'period':period,'days':days,'elapsed':elapsed,'cutoff_date':cutoff_date,'source':source,'state':'planned' if not elapsed and actual_as_of<start else 'closed' if elapsed==days else 'in_progress','half_usd':estimate,'half_brl':estimate*num(w.get('principal','Agosto 2026','F1')) if estimate is not None else None}
 results={x['id']:{'actual':x['actual'],'status':x['status'],**({'error':x['error']} if 'error' in x else {})} for x in r['rows']}
 formula_count=sum(x['kind'] in ('formula','external_quote') for x in data['cells'])
 formula_pass=sum(x['kind']=='formula' and x['status']=='pass' for x in r['rows'])
 summary={'counts':r['counts'],'formulas_total':formula_count,'formulas_recalculated':formula_pass,'frozen_quotes':sum(x['kind']=='external_quote' for x in r['rows']),'historical_boundaries':sum(x['kind']=='historical_boundary' for x in r['rows']),'as_of':actual_as_of.isoformat(),'period':period,'domain':domain['summary'],'native_additions':len(new),'status':'PARITY_PASS' if not r['issues'] and not domain['summary']['daily_failures'] and not domain['summary']['cash_failures'] and not domain['summary']['expense_failures'] and not new else 'SCENARIO_CHANGED','production_ready':False}
 if changes or native_catalog:summary['status']='SCENARIO_CHANGED'
 # All expected values remain in the immutable imported evidence only.
 domain.pop('checks');domain.pop('bindings');domain.pop('cash_checks')
 return {'currency_revision':'monthly-currency-1','network_revision':'monthly-networks-2','engine_revision':'finance-homologation-3','summary':summary,'domain':domain,'results':results,'issues':r['issues'],'boundaries':data['boundaries']}
if __name__=='__main__':
 result=run(json.load(sys.stdin));sys.stdout.write(json.dumps(result,ensure_ascii=False,default=json_default))
