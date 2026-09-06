"""Final read-only freshness check against canonical Sheets API. No source writes."""
import sys,pathlib,json,hashlib,collections
from urllib.parse import urlencode
root=pathlib.Path(__file__).parent
sys.path.insert(0,'/root/mgs-agent/work/finance-final-reaudit-1545877165982355557')
import audit
from import_snapshot import cells
source=json.loads((root/'private/source.json').read_text());directory=root/'private/live-readback';directory.mkdir(exist_ok=True)
results=[]
for book,meta in source['sources'].items():
 titles=sorted({x['sheet'] for x in source['cells'] if x['book']==book and x['kind']!='historical_boundary'})
 query=[('ranges',"'"+t.replace("'","''")+"'") for t in titles]+[('includeGridData','true'),('fields','spreadsheetId,sheets(properties,data(startRow,startColumn,rowData(values(userEnteredValue,effectiveValue,formattedValue))))')]
 drive=audit.get('https://www.googleapis.com/drive/v3/files/'+meta['id']+'?'+urlencode({'supportsAllDrives':'true','fields':'id,trashed,modifiedTime'}));assert not drive['trashed']
 data=audit.get('https://sheets.googleapis.com/v4/spreadsheets/'+meta['id']+'?'+urlencode(query));p=directory/(book+'.json');p.write_text(json.dumps(data,ensure_ascii=False))
 live={(s['properties']['title'],a):x for s in data['sheets'] for a,x in cells(s)};baseline={(x['sheet'],x['cell']):x for x in source['cells'] if x['book']==book and x['kind']!='historical_boundary'}
 changes=[]
 for key in sorted(set(live)|set(baseline)):
  old=baseline.get(key,{});new=live.get(key,{});uv=new.get('userEnteredValue',{});ev=next(iter(new.get('effectiveValue',{}).values()),'');f=uv.get('formulaValue','');prior=old.get('formula','')
  if f!=prior:changes.append({'sheet':key[0],'cell':key[1],'change':'formula'})
  if ev!=old.get('expected',''):changes.append({'sheet':key[0],'cell':key[1],'change':'value','quote':old.get('kind')=='external_quote'})
 results.append({'book':book,'source_cells':len(baseline),'live_cells':len(live),'changes':changes,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'modifiedTime':drive['modifiedTime']})
summary={'google_writes':0,'books':len(results),'formula_changes':sum(c['change']=='formula' for r in results for c in r['changes']),'value_changes':sum(c['change']=='value' for r in results for c in r['changes']),'details':results}
(directory/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in summary.items() if k!='details'}));print(json.dumps([{'book':r['book'],'changes':len(r['changes']),'first_changes':r['changes'][:8]} for r in results],ensure_ascii=False))
