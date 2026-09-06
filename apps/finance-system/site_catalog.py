"""Month-scoped native site registry and deterministic allocation bridge.
Source JSON/Sheets remain immutable. Derived allocation enters only a calculation-local
copy so the existing audited manager/payroll graph receives the same expense changes.
"""
import copy,calendar,re
from collections import OrderedDict
from calc import Workbook,num
from domain import project,daily,fx_convert
from expenses import migrate_expenses
from ui_model import apply_expense_changes
from periods import info as period_info
MONTH='Agosto 2026'
def catalog(segments,additions):
 groups=OrderedDict()
 for s in segments:
  if s.get('native_site'):continue
  g=groups.setdefault(s['site'],{'id':'site-'+s['id'],'name':s['site'],'status':s['status'],'segments':[],'countries':[],'units':0,'manager':s['manager'],'partner':s['partner'],'new':False})
  if s['status']!=g['status']:raise ValueError('Mixed legacy site status requires explicit reconciliation')
  g['segments'].append(s['id']);g['units']+=1;g['countries']=list(dict.fromkeys(g['countries']+s['countries']))
 byid={g['id']:g for g in groups.values()}
 for a in additions:
  if a.get('kind')!='site':continue
  if a.get('new'):
   if a['id'] in byid:raise ValueError('Duplicate native site')
   g={**a,'segments':[a['id']],'units':1};byid[g['id']]=g
  else:
   if a['id'] not in byid:raise ValueError('Unknown legacy site')
   byid[a['id']]['status']=a['status']
 for g in byid.values():
  if g['status'] not in ('ATIVO','INATIVO'):raise ValueError('Invalid site status')
 return list(byid.values())
def account_debits(additions,w):
 quotes={'USDBRL':w.get('principal',MONTH,'F1'),'USDCAD':w.get('principal',MONTH,'H1'),'GBPUSD':w.get('principal',MONTH,'I1')};out={}
 for a in additions:
  if a.get('kind')!='account_spend':continue
  out[a['fact_id']]=out.get(a['fact_id'],num(0))+abs(num(fx_convert(a['amount'],a['currency'],quotes)))
 return out
def prepare(data,overrides,additions,as_of=None):
 w=Workbook(data,overrides,as_of);period=data.get('_period','2026-08');start,days=period_info(period);base=project(data,w);sites=catalog(base['segments'],additions)
 enabled=period!='2026-08' or any(a.get('kind') in ('site','account_spend') or a.get('kind')=='expense' and a.get('category')=='company' for a in additions)
 if not enabled:return data,sites,False
 company=[a for a in additions if a.get('kind')=='expense' and a.get('category')=='company']
 rows=apply_expense_changes(migrate_expenses(w)['rows'],company,w.get('principal',MONTH,'F1'))
 total=sum((num(x['usd']) for x in rows if x['category']=='company'),num(0));active=sum(s['units'] for s in sites if s['status']=='ATIVO')
 if not active and total:raise ValueError('Mantenha ao menos um site ativo enquanto houver despesas da empresa')
 unit=total/active if active else num(0);states={seg:s['status'] for s in sites for seg in s['segments']}
 replacements={'B37':num(active),'O145':total}
 debits=account_debits(additions,w)
 for f in base['facts']:
  if f['id'] in debits:replacements[f['source']['spend']]=num(f['spend'])-debits[f['id']]
 for b in data['blocks']:
  label=b['name'].split('\n')[0].strip();slug=re.sub(r'[^a-z0-9]+','-',label.lower()).strip('-');seg=slug+('-principal' if b['header']==2 else '-complementar')
  status=states[seg];replacements[b['end']+str(b['header']-1)]=status
  for offset in range(31):
   valid=offset<days
   date=start.replace(day=offset+1) if valid else None
   replacements[b['metrics']['DESPESA_TOTAL']+str(b['sr']+offset)]=unit/days if valid and status=='ATIVO' and date<w.as_of else num(0)
 result=copy.copy(data);result['cells']=[]
 for c in data['cells']:
  if c['book']=='principal' and c['sheet']==MONTH and c['cell'] in replacements:
   c={**c,'kind':'input','input':replacements[c['cell']]};c.pop('formula',None)
  result['cells'].append(c)
 return result,sites,True

def apply_catalog(domain,sites,w):
 """Attach empty native days, update status, allocate new-site monthly share."""
 period=domain.get('period','2026-08');start,days=period_info(period)
 active=sum(s['units'] for s in sites if s['status']=='ATIVO');total=num(w.get('principal',MONTH,'O145'));unit=total/active if active else num(0)
 elapsed=min(days,max(0,(w.as_of-start).days))
 states={seg:s['status'] for s in sites for seg in s['segments']};newcost=[]
 for s in domain['segments']:s['status']=states[s['id']]
 for f in domain['facts']:f['status']=states.get(f['segment'],f['status'])
 for s in sites:
  if not s.get('new'):continue
  expense=unit*elapsed/days if s['status']=='ATIVO' else num(0)
  sitefacts=[f for f in domain['facts'] if f['site']==s['name']]
  for f in sitefacts:f['segment']=s['id'];f['status']=s['status']
  for country in s['countries']:
   for day in range(1,days+1):
    date=f'{period}-{day:02d}'
    if any(f['country']==country and f['date']==date for f in sitefacts):continue
    f={'id':s['id']+'|'+country+'|'+str(day),'segment':s['id'],'site':s['name'],'partner':s['partner'],'manager':s['manager'],'status':s['status'],'country':country,'date':date,**daily('',0,0,0,0),'source':{},'native_placeholder':True,'native_site_id':s['id'],'invalid_rate':w.get('principal',MONTH,s['invalid_source']),'share_rate':w.get('principal',MONTH,'EW82' if s['partner']=='M2' else 'D1'),'tax_rate':w.get('principal',MONTH,'C1')};domain['facts'].append(f);sitefacts.append(f)
  totals={k:sum((num(f[k]) for f in sitefacts),num(0)) for k in ['gross','invalid','net','tax','spend','profit']}
  domain['segments'].append({'id':s['id'],'name':s['name'],'site':s['name'],'partner':s['partner'],'manager':s['manager'],'status':s['status'],'countries':s['countries'],**totals,'expenses':expense,'profit_after_expenses':totals['profit']+expense,'native_site':True})
  newcost.append({'site':s['name'],'manager':s['manager'],'profit':expense,'invalid':num(0)})
 domain['site_catalog']=sites
 domain['allocation']={'period':period,'active_units':active,'legacy_units':43,'native':True,'company_expenses':total,'unallocated':total-sum((num(s['expenses']) for s in domain['segments']),num(0))}
 return newcost
