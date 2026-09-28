"""Explicit completed-data clock; immutable source and nominal facts stay intact."""
import json
from datetime import date,timedelta
from pathlib import Path
from calc import Workbook,num

def materialize_manager_totals(data,overrides,as_of):
 """Imported monthly totals may bypass daily cells; re-sum their same days."""
 w=Workbook(data,overrides,as_of);values={};present={r['id'] for r in data['cells']}
 layouts=json.loads((Path(__file__).parent/'manager-layouts.json').read_text())['managers']
 for m in layouts.values():
  for b in m['blocks']:
   for c in b['columns']:
    if 'ROI' in c['label'].upper():continue
    key=f"{m['book']}|Agosto 2026|{c['col']}{b['row']+33}"
    if key not in present:continue
    values[key]=sum((num(w.get(m['book'],'Agosto 2026',c['col']+str(b['row']+1+d))) for d in range(1,32)),num(0))
 cells=[]
 for c in data['cells']:
  if c['id'] in values:
   c={**c,'kind':'input','input':values[c['id']]};c.pop('formula',None)
  cells.append(c)
 return {**data,'cells':cells},{**overrides,**values}

def prepare(data,additions,period,start,days,as_of=None):
 actual=date.fromisoformat(as_of or data['as_of'])
 cuts=[a for a in additions if a.get('kind')=='data_cutoff']
 if len(cuts)>1:raise ValueError('Mais de uma data de corte')
 if not cuts:return data,actual,None
 cutoff=cuts[0].get('date')
 if cutoff is None:elapsed=0
 else:
  try:parsed=date.fromisoformat(cutoff)
  except (TypeError,ValueError):raise ValueError('Data de corte deve ser um dia completo da competência')
  if parsed.strftime('%Y-%m')!=period or parsed>=actual:raise ValueError('Data de corte deve ser um dia completo da competência')
  elapsed=parsed.day
 clock=start+timedelta(days=elapsed)
 # Manager imported daily cells are only a projection of complete facts.
 # Principal monetary leaves stay unchanged, including partial later days.
 layouts=json.loads((Path(__file__).parent/'manager-layouts.json').read_text())['managers']
 excluded={(m['book'],'Agosto 2026',c['col']+str(b['row']+1+day)) for m in layouts.values() for b in m['blocks'] for c in b['columns'] for day in range(elapsed+1,32)}
 cells=[]
 for c in data['cells']:
  if (c['book'],c['sheet'],c['cell']) in excluded:
   c={**c,'kind':'input','input':''};c.pop('formula',None)
  cells.append(c)
 present={c['id'] for c in cells}
 return {**data,'as_of':clock.isoformat(),'cells':cells},actual,{'cutoff_date':cutoff,'elapsed_days':elapsed,'source':cuts[0].get('source','explicit'),'blank_manager_inputs':['|'.join(key) for key in excluded if '|'.join(key) in present]}
