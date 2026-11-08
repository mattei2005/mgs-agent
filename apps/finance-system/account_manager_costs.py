"""Account-level spend attribution without guessing revenue allocation.
Only explicitly opted-in sites bridge native costs into manager results.
Legacy source-linked accounts already traverse the audited graph; never debit twice.
"""
from calc import num
from domain import fx_convert

def native_manager_costs(additions, sites, w, facts=None):
    enabled={s['name'] for s in sites if s.get('native_account_managers')}
    quotes={'USDBRL':w.get('principal','Agosto 2026','F1'),'USDCAD':w.get('principal','Agosto 2026','H1'),'GBPUSD':w.get('principal','Agosto 2026','I1')}
    rows=[]
    for a in additions:
        if a.get('kind')!='account_spend' or a.get('site') not in enabled or a.get('manager_key') not in ('joe','nicolas','kelly','isliago','george'):continue
        rows.append({'site':a['site'],'manager':a['manager_key'],'account_id':a['account_id'],'date':a['date'],'currency':a['currency'],'amount':a['amount'],'profit':-abs(num(fx_convert(a['amount'],a['currency'],quotes))),'invalid':num(0),'spend_only':True})
    # Explicit monthly opt-in for formerly unassigned legacy sites. The cost
    # already exists in company/site facts; this only bridges manager results.
    aliases={k:k for k in ('joe','nicolas','kelly','isliago','george')}
    aliases.update({'icaro':'george','ícaro':'george'})
    owners={s['name']:aliases[str(s.get('manager','')).strip().lower()] for s in sites
            if s['name'] in enabled and str(s.get('manager','')).strip().lower() in aliases}
    debits={}
    for a in additions:
        if a.get('kind')=='account_spend' and a.get('fact_id'):
            debits[a['fact_id']]=debits.get(a['fact_id'],num(0))+abs(num(fx_convert(a['amount'],a['currency'],quotes)))
    for f in facts or []:
        if (f.get('site') not in owners or f.get('native_addition') or f.get('native_placeholder')
                or str(f.get('manager','')).strip().upper()!='NÃO MAPEADO'):
            continue
        spend=num(f.get('spend',0))
        if spend>0:raise ValueError('Positive legacy spend requires explicit reconciliation')
        remaining=-spend-debits.get(f['id'],num(0))
        if remaining<0:raise ValueError('Native debit exceeds legacy fact spend')
        if not remaining:continue
        rows.append({'site':f['site'],'manager':owners[f['site']],'date':f['date'],
                     'currency':'USD','amount':str(remaining),'profit':-remaining,
                     'invalid':num(0),'spend_only':True,'legacy_source_spend':True,
                     'source_fact_id':f['id'],'country':f['country']})
    return rows
