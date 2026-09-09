"""Account-level spend attribution without guessing revenue allocation.
Only explicitly opted-in sites bridge native costs into manager results.
Legacy source-linked accounts already traverse the audited graph; never debit twice.
"""
from calc import num
from domain import fx_convert

def native_manager_costs(additions, sites, w):
    enabled={s['name'] for s in sites if s.get('native_account_managers')}
    quotes={'USDBRL':w.get('principal','Agosto 2026','F1'),'USDCAD':w.get('principal','Agosto 2026','H1'),'GBPUSD':w.get('principal','Agosto 2026','I1')}
    rows=[]
    for a in additions:
        if a.get('kind')!='account_spend' or a.get('site') not in enabled or a.get('manager_key') not in ('joe','nicolas','kelly','isliago','george'):continue
        rows.append({'site':a['site'],'manager':a['manager_key'],'account_id':a['account_id'],'date':a['date'],'currency':a['currency'],'amount':a['amount'],'profit':-abs(num(fx_convert(a['amount'],a['currency'],quotes))),'invalid':num(0),'spend_only':True})
    return rows
