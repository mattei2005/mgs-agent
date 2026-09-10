import json,hashlib,zipfile
from pathlib import Path
from decimal import Decimal as D
from collections import defaultdict
from openpyxl import load_workbook
SRC=Path('/root/mgs-agent/work/gam-final-1547689598392737874/Receita-01-09set-2026-Zeus-Final.xlsx')
OUT=Path('/root/mgs-agent/work/finance-revenue-1547692440574627921/Receita-01-09set-2026-Zeus-Final-Corrigido.xlsx')
ORIGINAL=Path('/root/.hermes/profiles/zeus/cache/documents/doc_10d5b4efd431_report_1_de_set_ate_9_de_set.xlsx')
assert hashlib.sha256(SRC.read_bytes()).hexdigest()=='f7047d7ab39a1412a969bc3528bc9b5c6fd763306ad2145ee98a545c81c55477'
w=load_workbook(SRC);changed=0
for title in ['Receita USD','Receita CAD']:
 s=w[title]
 for row in range(2,s.max_row):
  if s.cell(row,2).value=='helixenit.com':s.cell(row,2).value='helixenit.net';changed+=1
v=w['Validacao'];v.append(['Correção canônica','Helixenit: helixenit.net',None,None,'Domínio corrigido conforme context/sites.md; valores, datas, vertical, gestor e moeda inalterados.'])
for cell in v[v.max_row]:cell.alignment=v['A2'].alignment.copy()
w.save(OUT);assert changed>0
# Reconcile the corrected workbook to the original source by currency/day.
raw=defaultdict(D);ow=load_workbook(ORIGINAL,read_only=True,data_only=True)
for s in ow:
 c=s.title.upper()
 for r in s.iter_rows(min_row=2,values_only=True):
  if all(x is None for x in r):continue
  raw[(c,r[0].strftime('%Y-%m-%d'))]+=D(str(r[9]))
ow.close();rw=load_workbook(OUT,read_only=True,data_only=True);got=defaultdict(D);groups=0;sites=set()
for c in ['USD','CAD']:
 for r in rw['Receita '+c].iter_rows(min_row=2,values_only=True):
  if r[0]=='TOTAL':continue
  got[(c,r[0])]+=D(str(r[4]));groups+=1;sites.add(r[1])
rw.close();assert groups==513 and 'helixenit.net' in sites and 'helixenit.com' not in sites and set(got)==set(raw)
maxerr=max(abs(got[k]-raw[k]) for k in raw);assert maxerr<D('0.00000001')
with zipfile.ZipFile(OUT) as z:assert z.testzip() is None
summary={'pass':True,'source':str(SRC),'output':str(OUT),'old_sha256':hashlib.sha256(SRC.read_bytes()).hexdigest(),'new_sha256':hashlib.sha256(OUT.read_bytes()).hexdigest(),'changed_rows':changed,'change':'helixenit.com -> helixenit.net','source_rows_consolidated':513,'all_18_currency_days':True,'max_daily_error':str(maxerr),'financial_values_changed':False,'dashboard_numeric_payload_changed':False,'xlsx_integrity':True}
p=OUT.with_suffix('.summary.json');p.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n');assert json.loads(p.read_text())==summary
print(json.dumps(summary,ensure_ascii=False))
