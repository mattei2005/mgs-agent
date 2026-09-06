"""Read-only audit of active-site allocation, against canonical Sheets SA."""
import sys,pathlib,json,re,collections
from urllib.parse import urlencode
ROOT=pathlib.Path(__file__).resolve().parents[1];STATE=ROOT/'private/ui-layout-1546158286506561578';STATE.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT));sys.path.insert(0,'/root/mgs-agent/scripts')
from mgs_google_workspace_auth import service_account_access_token,api_json
import importlib.util
spec=importlib.util.spec_from_file_location('quotes',ROOT/'sync-quotes.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
quotes=mod.collect() # Includes selectors, identity, Drive/Sheets and quote formula gates; no publish.
token=service_account_access_token();source=json.loads((ROOT/'private/source.json').read_text())
lookup={x['cell']:x for x in source['cells'] if x['book']=='principal' and x['sheet']=='Agosto 2026'}
ranges=["'Agosto 2026'!A1:AMA1","'Agosto 2026'!A101:AZX101","'Agosto 2026'!B37","'Agosto 2026'!O145"]
for b in source['blocks']:
 co=b['metrics']['DESPESA_TOTAL'];ranges.extend([f"'Agosto 2026'!{co}{b['sr']}",f"'Agosto 2026'!{co}{b['totalrow']}"])
params=[('ranges',r) for r in dict.fromkeys(ranges)]+[('includeGridData','true'),('fields','spreadsheetId,sheets(properties(title),data(startRow,startColumn,rowData(values(userEnteredValue,effectiveValue,formattedValue))))')]
status,response=api_json('GET','https://sheets.googleapis.com/v4/spreadsheets/'+mod.SHEET+'?'+urlencode(params),token,quota_project='mgs-core-prod');assert status==200
(STATE/'sheet-allocation-readback.json').write_text(json.dumps(response,ensure_ascii=False))
from calc import col,Workbook,num
cells={}
for sh in response['sheets']:
 for block in sh.get('data',[]):
  for ri,row in enumerate(block.get('rowData',[]),block.get('startRow',0)+1):
   for ci,c in enumerate(row.get('values',[]),block.get('startColumn',0)+1):cells[col(ci)+str(ri)]=c
value=lambda a:next(iter(cells.get(a,{}).get('effectiveValue',{}).values()),'')
status_cells={a:value(a) for a in cells if value(a) in ('ATIVO','INATIVO')}
# Compare complete parsed block allocation coverage, not just Eggbev.
checks=[]
for b in source['blocks']:
 a=b['metrics']['DESPESA_TOTAL']+str(b['totalrow']);first=b['metrics']['DESPESA_TOTAL']+str(b['sr']);checks.append({'name':b['name'].split('\n')[0],'total_cell':a,'daily_cell':first,'formula':cells[first].get('userEnteredValue',{}).get('formulaValue'),'snapshot_formula_matches':cells[first].get('userEnteredValue',{}).get('formulaValue')==lookup[first].get('formula'),'live_total':value(a),'snapshot_total':lookup[a].get('expected'),'difference':float(num(value(a))-num(lookup[a].get('expected')))})
# In-memory source toggle only. Never persist modified source or write Google.
w=Workbook(source);before={'active':w.get('principal','Agosto 2026','B37'),'egg_expenses':w.get('principal','Agosto 2026','LW36')}
import copy
modified=copy.deepcopy(source)
for c in modified['cells']:
 if c['id']=='principal|Agosto 2026|MB1':c['input']='INATIVO'
w2=Workbook(modified);after={'active':w2.get('principal','Agosto 2026','B37'),'egg_expenses':w2.get('principal','Agosto 2026','LW36')}
assert num(before['active'])-num(after['active'])==1 and num(after['egg_expenses'])==0
out={'pass':True,'google_writes':0,'quote_read':quotes,'status_counts':dict(collections.Counter(status_cells.values())),'denominator':value('B37'),'denominator_formula':cells['B37']['userEnteredValue']['formulaValue'],'company_expenses':value('O145'),'allocation_checks':checks,'in_memory_toggle':{'before':before,'after':after},'snapshot_status_differences':[a for a,v in status_cells.items() if lookup.get(a,{}).get('input')!=v]}
from calc import json_default
(STATE/'allocation-audit.json').write_text(json.dumps(out,ensure_ascii=False,indent=2,default=json_default))
print(json.dumps({'pass':True,'status_counts':out['status_counts'],'denominator':out['denominator'],'company_expenses':out['company_expenses'],'blocks_checked':len(checks),'formula_differences':sum(not c['snapshot_formula_matches'] for c in checks),'total_differences':sum(abs(c['difference'])>1e-7 for c in checks),'status_differences':out['snapshot_status_differences'],'toggle':out['in_memory_toggle'],'google_writes':0},default=json_default))
