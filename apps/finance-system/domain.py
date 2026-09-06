"""Coordinate-free financial primitives and normalized migration projection.

The primitives below never access spreadsheets. project() is the bounded import
adapter; source addresses are lineage, never entity identity or new-entry rules.
"""
import re,json,pathlib,calendar,collections
from datetime import date,timedelta
from periods import info as period_info
from decimal import Decimal as D
from calc import Workbook,export,equal,num,numeric,col,ci,address,json_default
MONTH='Agosto 2026'

def daily(gross,spend,invalid_rate,share_rate,tax_rate):
 g=None if gross in ('',None) else D(str(gross));s=D(str(spend or 0));iv=D(str(invalid_rate));share=D(str(share_rate));tax=D(str(tax_rate))
 if any(not D(0)<=x<=D(1) for x in (iv,share,tax)):raise ValueError('rates must be between 0 and 1')
 invalid='' if g is None else -g*iv
 net='' if g is None else (g+invalid)*(1-share)
 taxes='' if g is None else -net*tax
 profit=num(net)+num(taxes)+s
 rg='' if not s else num(g)/abs(s)-1
 rn='' if not s else num(net)/(abs(s)+abs(num(taxes)))-1
 return dict(gross='' if g is None else g,invalid=invalid,net=net,tax=taxes,spend=s,profit=profit,roi_gross=rg,roi_net=rn)
def project_month(total,start,as_of):
 start=date.fromisoformat(start);as_of=date.fromisoformat(as_of);days=calendar.monthrange(start.year,start.month)[1];elapsed=min(days,max(0,(as_of-start).days))
 return '' if not elapsed else D(str(total))*days/elapsed
def fx_convert(amount,currency,quotes):
 if amount in ('',None):return ''
 v=D(str(amount))
 if currency=='USD':return v
 if currency=='CAD':return v/D(str(quotes['USDCAD']))
 if currency=='GBP':return v*D(str(quotes['GBPUSD']))
 if currency=='BRL':return v/D(str(quotes['USDBRL']))
 raise ValueError('unsupported currency')
def portfolio(facts,company_expenses,personnel,usdbrl):
 total={k:sum((num(f[k]) for f in facts),D(0)) for k in ('gross','invalid','net','tax','spend','profit')}
 profit=total['profit']+num(company_expenses)+num(personnel)
 total.update(company_expenses=num(company_expenses),personnel=num(personnel),profit=profit,half_usd=profit/2,half_brl=profit/2*num(usdbrl),roi_media=profit/abs(total['spend']) if total['spend'] else '')
 return total

def project(data,w):
 period=data.get('_period','2026-08');start,days=period_info(period)
 get=lambda c:w.get('principal',MONTH,c)
 src=lambda c:w.records.get(('principal',MONTH,c),{})
 def fixed_rate(c):
  refs=re.findall(r'\$([A-Z]+)\$(\d+)',src(c).get('formula',''))
  if len(set(refs))!=1:raise ValueError('Rate binding not uniquely identified '+c)
  co,r=refs[0];return num(get(co+r)),co+r
 base={x['cell']:x for x in data['cells'] if x['book']=='principal' and x['sheet']=='BASE_DASH'}
 basev=lambda c:base.get(c,{}).get('input',base.get(c,{}).get('expected',''))
 # Only descriptive metadata is accepted from BASE_DASH; no numeric results.
 metadata={}
 for r in range(2,155):
  if basev('C'+str(r))=='SITE':
   binding=base.get('N'+str(r),{}).get('formula','')
   match=re.fullmatch(r"='Agosto 2026'!([A-Z]+\d+)",binding)
   if not match:raise ValueError('Unresolved segment metadata binding')
   metadata[match[1]]={k:basev(co+str(r)) for k,co in [('partner','E'),('site','F'),('manager','G'),('managers','H'),('status','I'),('segment','D')]}
 facts=[];segments=[];checks=[];bindings={};domain_checks=[]
 for idx,b in enumerate(data['blocks']):
  # Stable identity from business label + occurrence; never use column position.
  label=b['name'].split('\n')[0].strip();slug=re.sub(r'[^a-z0-9]+','-',label.lower()).strip('-');segment=slug+('-principal' if b['header']==2 else '-complementar')
  meta=metadata[b['metrics']['RECEITA_NET_TOTAL']+str(b['totalrow'])]
  metrics=b['metrics'];countries=[h.split('_')[-1] for h in metrics if h.startswith('GROSS_USD_') or h=='GROSS_BR'];summaries=[]
  for country in countries:
   fields={}
   for key,pref in [('gross','GROSS_USD_'),('invalid','INVALIDO_'),('net','NET_USD_'),('tax','IMPOSTO_'),('spend','GASTOS_'),('profit','LUCRO_LIQUIDO_'),('roi_gross','ROI_GROSS_'),('roi_net','ROI_NET_')]:
    header=pref+country
    if header not in metrics and country=='BR' and key in ('gross','net'):header='GROSS_BR' if key=='gross' else 'NET_BR'
    fields[key]=metrics[header]
   for offset in range(days):
    r=str(b['sr']+offset);iv,ivref=fixed_rate(fields['invalid']+r);share,sref=fixed_rate(fields['net']+r);tax,tref=fixed_rate(fields['tax']+r)
    gross=get(fields['gross']+r);spend=get(fields['spend']+r);values=daily(gross,spend,iv,share,tax)
    row={'id':segment+'|'+country+'|'+str(offset+1),'segment':segment,'site':meta.get('site',label),'partner':meta.get('partner','NAO_MAPEADO'),'manager':meta.get('manager','NAO_MAPEADO'),'status':meta.get('status','NAO_MAPEADO'),'country':country,'date':f'{period}-{offset+1:02d}',**values,'invalid_rate':iv,'share_rate':share,'tax_rate':tax,'source':{k:v+r for k,v in fields.items()},'rate_source':{'invalid':ivref,'share':sref,'tax':tref}}
    facts.append(row)
    for metric,value in values.items():
     expected=get(fields[metric]+r)
     # Daily empty gross but zero spend produces numeric zero profit by source convention.
     checks.append({'id':row['id']+'|'+metric,'source':fields[metric]+r,'actual':value,'expected':expected,'pass':equal(value,expected)})
     bindings[fields[metric]+r]={'label':label+' · '+country+' · '+row['date']+' · '+metric,'domain':metric,'segment':segment,'country':country}
  segment_facts=[f for f in facts if f['segment']==segment]
  totals={k:sum((num(f[k]) for f in segment_facts),D(0)) for k in ('gross','invalid','net','tax','spend','profit')}
  expense=num(get(metrics['DESPESA_TOTAL']+str(b['totalrow'])))
  segments.append({'id':segment,'name':label,'site':meta.get('site',label),'partner':meta.get('partner','NAO_MAPEADO'),'manager':meta.get('manager','NAO_MAPEADO'),'status':meta.get('status','NAO_MAPEADO'),'countries':countries,**totals,'expenses':expense,'profit_after_expenses':totals['profit']+expense,'source':b['start']+str(b['header'])})
 cash=portfolio(facts,get('O145'),get('O161'),get('F1'))
 cash_bind={'gross':'J58','invalid':None,'tax':'J71','spend':'J75','company_expenses':'J72','personnel':'J73','profit':'J77','half_usd':'J80','half_brl':'J81','roi_media':'J79'}
 for metric,cell in cash_bind.items():
  if cell:domain_checks.append({'metric':metric,'source':cell,'actual':cash[metric],'expected':w.get('principal','CAIXA SINTETICO',cell),'pass':equal(cash[metric],w.get('principal','CAIXA SINTETICO',cell))})
 cashrows=[]
 for r in range(1,82):
  value=w.get('principal','CAIXA SINTETICO','J'+str(r));label=w.get('principal','CAIXA SINTETICO','B'+str(r));partner=w.get('principal','CAIXA SINTETICO','A'+str(r))
  if value!='' or label!='':cashrows.append({'row':r,'label':label,'partner':partner,'actual':value,'source':'J'+str(r)})
 managers=[]
 for name in data.get('manager_mapping',{}):
  for r in list(range(2,13))+[14]:
   label=w.get(name,MONTH,'B'+str(r))
   if label=='' and r not in (12,14):continue
   vals={k:w.get(name,MONTH,co+str(r)) for k,co in [('invalid','C'),('profit','D'),('commission7','E'),('commission10','F')]}
   managers.append({'manager':name,'label':label or ('Total' if r==12 else 'Projeção'),'row':r,**vals})
 return {'period':period,'facts':facts,'segments':segments,'cash':cash,'cash_rows':cashrows,'managers':managers,'bindings':bindings,'checks':checks,'cash_checks':domain_checks,'summary':{'daily_checks':len(checks),'daily_failures':sum(not c['pass'] for c in checks),'cash_checks':len(domain_checks),'cash_failures':sum(not c['pass'] for c in domain_checks)}}

if __name__=='__main__':
 root=pathlib.Path(__file__).parent;data=json.loads((root/'private/source.json').read_text());w=Workbook(data);p=project(data,w)
 (root/'private/domain.json').write_text(json.dumps(p,ensure_ascii=False,default=json_default));print(json.dumps(p['summary']));print(json.dumps([c for c in p['checks']+p['cash_checks'] if not c['pass']][:10],default=json_default))
