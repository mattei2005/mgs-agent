import json,hashlib,warnings
from pathlib import Path
from collections import defaultdict
from decimal import Decimal
import openpyxl
warnings.filterwarnings('ignore',category=UserWarning,module='openpyxl')
ROOT=Path(__file__).parent
CACHE=Path('/root/.hermes/profiles/zeus/cache/documents')
NAMES=['doc_e96375988e6f_Report_Digital_Trust_adx_2-2.xlsx','doc_cea2ea9137dd_Report_Digital_Trust_adx_2.xlsx','doc_17157e0638b2_Digital_Trust-2.xlsx','doc_1d82160fd565_Digital_Trust.xlsx','doc_08afc61168ab_Receita-07-08set-2026.xlsx']
def dump(name,obj): (ROOT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2,default=str))
raw=[]; manifest=[]; claude=[]
for i,name in enumerate(NAMES):
 p=CACHE/name; w=openpyxl.load_workbook(p,read_only=True,data_only=False); sheets=[]
 for s in w:
  rows=list(s.values); sheets.append({'name':s.title,'rows':len(rows),'cols':s.max_column,'formula_count':sum(isinstance(v,str) and v.startswith('=') for r in rows for v in r)})
 if i<4:
  props=dict(w.worksheets[0].values); curr=props.get('Report currency',props.get('Moeda do relatório')); s=w.worksheets[1]; rows=list(s.values)
  for n,r in enumerate(rows[1:],2):
   assert len(r)==10 and str(r[0]).startswith('2026-09-') and isinstance(r[9],(float,int)), (name,n,r)
   raw.append({'file':name,'row':n,'currency':curr,'date':str(r[0])[:10],'placement':r[1],'medium':r[2],'campaign':r[3],'content':r[4],'term':r[5] if curr=='CAD' else None,'impressions':r[6],'clicks':r[7],'revenue':str(r[9])})
  extra={'properties':props,'data_count':len(rows)-1,'total':str(sum((Decimal(str(r[9])) for r in rows[1:]),Decimal(0)))}
 else:
  extra={}
  for s in w:
   for n,r in enumerate(list(s.values)[1:],2):
    claude.append({'sheet':s.title,'row':n,'currency':s.title.split()[-1],'date':r[0],'site':r[1],'vertical':r[2],'manager':r[3],'revenue':str(r[4])})
 manifest.append({'file':name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'sheets':sheets,**extra})
assert len(manifest)==5
by=defaultdict(lambda:Decimal(0))
for r in raw: by[(r['currency'],r['date'],r['placement'],r['medium'])]+=Decimal(r['revenue'])
groups=[dict(zip(['currency','date','placement','medium','revenue'],[*k,str(v)])) for k,v in sorted(by.items())]
dump('manifest.json',manifest);dump('raw.json',raw);dump('claude.json',claude);dump('raw-groups.json',groups)
print(json.dumps({'manifest':manifest,'raw_count':len(raw),'group_count':len(groups),'claude_data_count':sum(r['date']!='TOTAL' for r in claude)},ensure_ascii=False))
print('CLAUDE_ROWS')
for r in claude: print(json.dumps(r,ensure_ascii=False))
print('RAW_PLACEMENTS')
for k in sorted(set((r['currency'],r['placement']) for r in raw)):print(k)
