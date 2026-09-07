"""Native company-expense and payroll rules, separated from migration coordinates."""
from decimal import Decimal as D
import re
from calc import num,equal
from domain import project_month

def compensation(projected_profit_usd,usdbrl,floor_brl='3000',low_rate='.07',high_rate='.10',high_threshold_brl='100000'):
 p=num(projected_profit_usd);fx=num(usdbrl);floor=num(floor_brl);low=num(low_rate);high=num(high_rate)
 if fx<=0 or low<=0:raise ValueError('Invalid exchange or commission rule')
 brl=p*fx
 if brl<=floor/low:return -(floor/fx)
 if brl<num(high_threshold_brl):return -(p*low)
 return -(p*high)

def apply_payroll_policy(rows,changes,managers,fx):
 """Explicit operational policy, leaving immutable migration parity untouched.
 Commission uses actual monthly attributed net, not projected future revenue.
 BRL payroll is rounded half-up to cents before USD conversion.
 """
 from copy import deepcopy
 from decimal import ROUND_HALF_UP
 output=deepcopy(rows);fx=num(fx)
 if fx<=0:raise ValueError('Invalid payroll exchange')
 configs={a.get('target') or a['id']:a for a in changes if a.get('payroll_rule')=='monthly-v1'}
 for row in output:
  cfg=configs.get(row['id'])
  if not cfg:continue
  if row['category']!='personnel':raise ValueError('Payroll policy on non-personnel row')
  activity=cfg.get('activity','ATIVO')
  if activity not in ('ATIVO','INATIVO'):raise ValueError('Invalid employee activity')
  row.update(activity=activity,payroll_rule='monthly-v1')
  if activity=='INATIVO' or row.get('archived'):
   row.update(usd=D(0),brl=D(0));continue
  if row.get('manager'):
   totals=[m for m in managers if m['manager']==row['manager'] and m['row']==12]
   if len(totals)!=1:raise ValueError('Monthly manager result not uniquely mapped')
   profit=num(totals[0]['profit']);base=profit*fx
   brl=(compensation(profit,fx)*fx).quantize(D('.01'),rounding=ROUND_HALF_UP)
   row.update(usd=brl/fx,brl=brl,commission_base_brl=base,commission_rate=D('.10') if base>=D(100000) else D('.07'),floor_brl=D(3000))
  elif cfg.get('manager_role'):
   raise ValueError('Active manager requires an explicit result mapping')
 return output

def migrate_expenses(w):
 get=lambda c:w.get('principal','Agosto 2026',c)
 records=w.records;rows=[];checks=[];fx=get('F1')
 for r in list(range(100,145))+list(range(148,161)):
  source=records.get(('principal','Agosto 2026','O'+str(r)),{});formula=source.get('formula','');label=get('M'+str(r))
  if not label and not source:continue
  payroll=r>=148;mode='USD';origin='O'+str(r);value=None;manager=None
  if not formula:value=num(get(origin))
  elif re.fullmatch(r'=SUM\(P'+str(r)+r'/\$F\$1\)',formula):
   mode='BRL';origin='P'+str(r);value=num(get(origin))/num(fx)
  elif re.fullmatch(r'=SUM\(R'+str(r)+r'/\$([GH])\$1\)\*-1',formula):
   binding=re.fullmatch(r'=SUM\(R'+str(r)+r'/\$([GH])\$1\)\*-1',formula)[1];mode='UNIT_COST_DIVISOR' if binding=='G' else 'CAD';origin='R'+str(r);value=-num(get(origin))/num(get(binding+'1'))
  elif payroll and 'IMPORTRANGE' in formula:
   ids=set(re.findall(r'IMPORTRANGE\("([\w-]+)"',formula))
   if len(ids)!=1:raise ValueError('Ambiguous payroll import')
   manager=w.ids[next(iter(ids))];projected=w.get(manager,'Agosto 2026','D14');value=compensation(projected,fx);mode='COMMISSION_FLOOR';origin=manager+'|projected_profit'
  else:raise ValueError('Unsupported expense rule at '+str(r))
  target=get('O'+str(r));checks.append({'source':'O'+str(r),'actual':value,'expected':num(target),'pass':equal(value,num(target))})
  rows.append({'id':('personnel' if payroll else 'company')+'|'+str(r),'label':label,'category':'personnel' if payroll else 'company','mode':mode,'origin':origin,'input':get(origin) if '|' not in origin else None,'usd':value,'brl':value*num(fx),'source':'O'+str(r),'manager':manager})
 totals={k:sum((x['usd'] for x in rows if x['category']==k),D(0)) for k in ['company','personnel']}
 for k,target in [('company','O145'),('personnel','O161')]:checks.append({'source':target,'actual':totals[k],'expected':get(target),'pass':equal(totals[k],get(target))})
 return {'rows':rows,'totals':totals,'checks':checks,'summary':{'checks':len(checks),'failures':sum(not x['pass'] for x in checks)}}
