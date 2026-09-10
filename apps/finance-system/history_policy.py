"""Reapply confirmed dashboard-only historical corrections after a fresh Sheet capture."""
import copy,hashlib,json,re
from collections import Counter
from decimal import Decimal as D,ROUND_HALF_UP
from calc import export,numeric
AUTH='1547697182948458611'
def col(n):
 s=''
 while n:n,r=divmod(n-1,26);s=chr(65+r)+s
 return s
def convert(book,sheet,cell):
 u=cell.get('userEnteredValue',{});e=cell.get('effectiveValue',{});value=next(iter(e.values()),'');formula=u.get('formulaValue','');row={'id':f'{book}|{sheet}|{cell["a1"]}','book':book,'sheet':sheet,'cell':cell['a1'],'expected':value,'formatted':cell.get('formattedValue',''),'format':cell.get('effectiveFormat',{}).get('numberFormat',{})}
 boundary='COUNTA(' in formula.upper() or 'AVERAGEIF(' in formula.upper() or 'Junho 2026' in formula or 'CAIXA SINTETICO' in formula
 if boundary:row.update(input=value,kind='historical_boundary',source_formula=formula)
 elif formula:
  row.update(formula=formula,kind='external_quote' if 'GOOGLEFINANCE' in formula else 'formula')
  if 'GOOGLEFINANCE' in formula:row['input']=value
 elif u:row.update(input=next(iter(u.values())),kind='input')
 else:row.update(input=value,kind='spill_or_label')
 return row
def format_value(value,spec):
 q=value.quantize(D('0.01'),rounding=ROUND_HALF_UP);pattern=spec.get('pattern','')
 if spec.get('type')=='PERCENT':return f'{(value*100).quantize(D("0.01"),rounding=ROUND_HALF_UP):.2f}%'
 number=f'{abs(q):,.2f}'
 if '[$R$' in pattern:return f' R$  ({number})' if q<0 else (f' R$  {number} ' if q>0 else ' R$  -')
 if pattern.startswith('_($*'):return f' $ ({number})' if q<0 else (f' $ {number} ' if q>0 else ' $ -')
 return f' $  ({number})' if q<0 else (f' $  {number} ' if q>0 else ' $  -')
def refresh_embedded(obj,changed):
 if not isinstance(obj,(dict,list)):return
 if isinstance(obj,list):
  for v in obj:refresh_embedded(v,changed)
  return
 ref=obj.get('reference',obj.get('a1'))
 if ref in changed:
  c=changed[ref]
  if 'raw' in obj:obj['raw']=str(c['value'])
  if 'value' in obj:obj['value']=c['value']
  if 'formatted' in obj:obj['formatted']=c['formatted']
  if 'kind' in obj:obj['kind']='numberValue'
 for k,v in obj.items():
  if k!='cells':refresh_embedded(v,changed)
def apply_july_sb_tech_cad(documents,raw_by_book):
 assert len(documents)==6 and {d['book'] for d in documents}==set(raw_by_book) and {d['period'] for d in documents}=={'2026-07'}
 sources={d['book']:{'id':d['source_id']} for d in documents};cells=[convert(book,'Julho 2026',c) for book,rows in raw_by_book.items() for c in rows];base={'as_of':'2026-09-10','sources':sources,'cells':cells};_,old=export(base);assert old['counts'].get('error',0)==0,old['issues'][:5];changed=copy.deepcopy(base);target=next(x for x in changed['cells'] if x['id']=='principal|Julho 2026|N140');assert target.get('formula') in ('=SUM(Q140/$I$1)*-1','=SUM(Q140/$H$1)*-1')
 if target['formula']=='=SUM(Q140/$H$1)*-1':return documents,{'applied':False,'reason':'source_already_cad','changed_cells':0}
 target['formula']='=SUM(Q140/$H$1)*-1';_,pre=export(changed);pr={x['id']:x for x in pre['rows']}
 for column in ('AMZ','ANA'):
  values=[pr[f'principal|Julho 2026|{column}{row}']['actual'] for row in range(5,36) if f'principal|Julho 2026|{column}{row}' in pr];values=[v for v in values if numeric(v) and v!=0];assert values;aggregate=next(x for x in changed['cells'] if x['id']==f'principal|Julho 2026|{column}36');assert aggregate['kind']=='historical_boundary';aggregate['input']=sum(values,D(0))/D(len(values))
 _,new=export(changed);assert new['counts'].get('error',0)==0,new['issues'][:5];old_rows={x['id']:x for x in old['rows']};new_rows={x['id']:x for x in new['rows']};deltas=[]
 for ident,before in old_rows.items():
  after=new_rows[ident];a,b=before.get('actual'),after.get('actual')
  if numeric(a) and numeric(b) and a!=b:
   source=next(x for x in base['cells'] if x['id']==ident);deltas.append({'book':source['book'],'cell':source['cell'],'delta':b-a,'format':source['format']})
 assert len(deltas)>1000;bydoc={d['book']:copy.deepcopy(d) for d in documents};counts=Counter()
 for book,doc in bydoc.items():
  cells={c['a1']:c for c in doc['cells']};changed_cells={}
  for delta in [x for x in deltas if x['book']==book]:
   c=cells.get(delta['cell']);assert c and c['kind']=='numberValue';value=D(str(c['value']))+delta['delta'];c['value']=float(value);c['formatted']=format_value(value,delta['format']);changed_cells[c['a1']]=c;counts[book]+=1
  refresh_embedded(doc,changed_cells);upstream=doc['source_sha256'];doc['upstream_source_sha256']=upstream;doc['source']='original-monthly-tab+dashboard-authorized-correction';doc['source_authority']=doc.get('source_authority');doc['correction']={'authority':AUTH,'expense_id':'company|142','label':'SB Tech Bot','amount':'629.28','currency':'CAD','supersedes_live_formula':'I1/GBP','changed_cells':counts[book],'source_sheet_write':False};doc['source_sha256']=hashlib.sha256(json.dumps(doc['cells'],sort_keys=True).encode()).hexdigest()
 principal=bydoc['principal'];assert principal['closure']['balance']['reference']=='F132';return [bydoc[d['book']] for d in documents],{'applied':True,'authority':AUTH,'changed_cells':sum(counts.values()),'by_book':dict(counts),'july_due':principal['closure']['due'],'july_balance':principal['closure']['balance']}
