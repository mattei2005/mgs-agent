"""UI lineage adapter. Traverses the existing parsed graph; no new finance formulas."""
import json,pathlib,re,copy,functools
from decimal import Decimal as D
from calc import Workbook,parse,col,address,numeric,num,json_default
from domain import MONTH

def build_model(data):
 w=Workbook(data);inputs={};fact_map={}
 @functools.lru_cache(maxsize=None)
 def leaves(key,trail=()):
  if key in trail or len(trail)>80:return ()
  b,s,c=key;r,co=address(c)
  if s!=MONTH or r<=1:return ()
  if key in w.spills:return leaves(w.spills[key],trail+(key,))
  x=w.records.get(key,{})
  if x.get('kind') in ('external_quote','historical_boundary'):return ()
  if not x.get('formula'):
   v=x.get('input','')
   return (key,) if v=='' or numeric(v) else ()
  found=set()
  def visit(n):
   if not isinstance(n,tuple):return
   rr=w.reference(n,b,s,c) if n[0]=='ref' or n[0]=='call' and n[1] in ('IMPORTRANGE','INDEX') else None
   if rr:
    if (rr.r2-rr.r1+1)*(rr.c2-rr.c1+1)>3000:raise ValueError('Unbounded UI lineage')
    for row in range(rr.r1,rr.r2+1):
     for cc in range(rr.c1,rr.c2+1):found.update(leaves((rr.book,rr.sheet,col(cc)+str(row)),trail+(key,)))
    return
   if n[0]=='call':
    for a in n[2]:visit(a)
   elif n[0] in ('bin','unary'):
    for a in n[2:]:visit(a)
   elif n[0]=='array':
    for row in n[1]:
     for a in row:visit(a)
  visit(parse(x['formula']));return tuple(sorted(found))
 ownership={}
 for manager,m in data.get('manager_mapping',{}).items():
  for link in m['mapping']:
   if not link['cell'].startswith('D'):continue
   for origin in link.get('found',[]):
    for key in leaves(('principal',MONTH,origin['source'])):ownership.setdefault(key,set()).add(manager)
 def descriptor(key,metric,currency):
  b,s,c=key;r,co=address(c);x=w.records.get(key,{})
  headers=[];currency_headers=[]
  for rr in range(max(2,r-40),r):
   rec=w.records.get((b,s,col(co)+str(rr)),{});v=rec.get('input','')
   if metric=='spend' and isinstance(v,str) and v.strip() in ('R$','BRL','BM - $','USD','CAD'):currency_headers.append(v.strip())
   if isinstance(v,str) and v.strip() and v not in ('ESTA','Preencher','R$','BM - $') and not re.fullmatch(r'\d+',v):headers.append(v.replace('\n',' · ').strip())
  if currency_headers:currency={'R$':'BRL','BRL':'BRL','CAD':'CAD'}.get(currency_headers[-1],'USD')
  return {'key':'|'.join(key),'value':x.get('input',''),'metric':metric,'currency':currency,'label':headers[-1] if metric=='spend' and headers else ('Receita' if metric=='gross' else 'Conta de anúncio'),'managers':sorted(ownership.get(key,set())),'source':c,'book':b}
 for block in data['blocks']:
  label=block['name'].split('\n')[0].strip();slug=re.sub(r'[^a-z0-9]+','-',label.lower()).strip('-');segment=slug+('-principal' if block['header']==2 else '-complementar');metrics=block['metrics']
  countries=[h.split('_')[-1] for h in metrics if h.startswith('GROSS_USD_') or h=='GROSS_BR']
  for country in countries:
   for day in range(31):
    mapping={};r=block['sr']+day
    for metric,prefix in [('gross','GROSS_USD_'),('spend','GASTOS_')]:
     name=prefix+country
     if name not in metrics and metric=='gross' and country=='BR':name='GROSS_BR'
     keys=leaves(('principal',MONTH,metrics[name]+str(r)));mapping[metric]=[]
     currency='CAD' if 'GROSS_CAD_'+country in metrics and metric=='gross' else 'GBP' if 'GROSS_GBP_'+country in metrics and metric=='gross' else 'USD'
     for key in keys:
      ident='|'.join(key);item=descriptor(key,metric,currency);inputs.setdefault(ident,item);mapping[metric].append(ident)
    fact_map[segment+'|'+country+'|'+str(day+1)]=mapping
 expenses={}
 for r in list(range(100,145))+list(range(148,161)):
  cat='personnel' if r>=148 else 'company';q=w.records.get(('principal',MONTH,'Q'+str(r)),{})
  expenses[cat+'|'+str(r)]={'status':q.get('input',q.get('expected','')) or 'Não informado'}
 return {'facts':fact_map,'inputs':inputs,'expenses':expenses,'version':1}

def prepare_inputs(data,overrides,model):
 """Materialize only verified blank leaves in a calculation-local copy."""
 cells=list(data['cells']);known={x['id'] for x in cells}
 for key,value in overrides.items():
  if key in model['inputs'] and key not in known:
   b,s,c=key.split('|');cells.append({'id':key,'book':b,'sheet':s,'cell':c,'kind':'input','input':0,'expected':'','formatted':''})
 return {**data,'cells':cells}

def apply_expense_changes(rows,changes,fx):
 output=copy.deepcopy(rows);by_id={x['id']:x for x in output}
 for a in changes:
  if a.get('kind')!='expense':continue
  target=a.get('target') or a['id'];row=by_id.get(target)
  if row is None:
   row={'id':target,'category':a['category'],'label':a.get('label',''),'mode':'EXTRA','origin':'Lançamento na dash','source':'','manager':None,'usd':D(0),'brl':D(0),'extra':True};output.append(row);by_id[target]=row
  row.update(label=a.get('label',row['label']),status=a.get('status','Não informado'),checked_on=a.get('checked_on'),archived=a.get('archived',False))
  if 'amount' in a:
   if row['mode']=='COMMISSION_FLOOR':raise ValueError('Calculated payroll cannot be overridden')
   amount=-abs(num(a['amount']));usd=amount/num(fx) if a['currency']=='BRL' else amount
   row.update(usd=usd,brl=usd*num(fx),edited=True,edit_amount=a['amount'],edit_currency=a['currency'])
  if row['archived']:row.update(archived_usd=row['usd'],archived_brl=row['brl'],usd=D(0),brl=D(0))
 return output

if __name__=='__main__':
 root=pathlib.Path(__file__).parent;data=json.loads((root/'private/source.json').read_text());print(json.dumps(build_model(data),ensure_ascii=False,default=json_default))
