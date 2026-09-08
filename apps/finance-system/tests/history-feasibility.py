"""Read-only Jan-Jul2026 feasibility snapshots; no Sheet or dashboard mutation."""
import sys,pathlib,json,datetime,re,time,hashlib,unicodedata,urllib.parse
R=pathlib.Path(__file__).resolve().parents[1];D=R/'private/history-feasibility-1546757745078968381';D.mkdir(mode=0o700,parents=True,exist_ok=True)
sys.path.insert(0,'/root/mgs-agent/scripts');from mgs_google_workspace_auth import load_env,load_service_account,service_account_access_token,api_json
load_env();sa=load_service_account();assert sa['project_id']=='mgs-core-prod' and sa['client_email']=='mgsagent@mgs-core-prod.iam.gserviceaccount.com'
token=service_account_access_token();names=['Janeiro','Fevereiro','Março','Abril','Maio','Junho','Julho']
def norm(s):return ''.join(c for c in unicodedata.normalize('NFKD',s).lower() if not unicodedata.combining(c))
def save(name,data):
 p=D/name;p.write_text(json.dumps(data,ensure_ascii=False));p.chmod(0o600);return hashlib.sha256(p.read_bytes()).hexdigest()
def col(n):
 out=''
 while n:n,k=divmod(n-1,26);out=chr(65+k)+out
 return out
def metadata():
 sources=json.loads((R/'private/source.json').read_text())['sources'];out=[]
 for key,v in sources.items():
  sid=v['id'];status,drive=api_json('GET',f'https://www.googleapis.com/drive/v3/files/{sid}?'+urllib.parse.urlencode({'supportsAllDrives':'true','fields':'id,name,mimeType,trashed,modifiedTime'}),token);assert status==200 and not drive['trashed']
  status,m=api_json('GET',f'https://sheets.googleapis.com/v4/spreadsheets/{sid}?fields=spreadsheetId,properties,sheets.properties',token);assert status==200
  tabs=[s['properties'] for s in m['sheets']];selected=[]
  for i,name in enumerate(names,1):
   candidates=[s for s in tabs if norm(s['title']).strip()==norm(name+' 2026')];selected.append({'month':f'2026-{i:02d}','matches':candidates})
  out.append({'key':key,'id':sid,'drive':drive,'properties':m['properties'],'tabs':tabs,'selected':selected});save('metadata.json',out)
 print(json.dumps([{'key':x['key'],'title':x['drive']['name'],'months':[{'month':m['month'],'tabs':[s['title'] for s in m['matches']]} for m in x['selected']]} for x in out],ensure_ascii=False))
def capture(key):
 book=next(x for x in json.loads((D/'metadata.json').read_text()) if x['key']==key);rows=[]
 for m in book['selected']:
  if len(m['matches'])!=1:rows.append({'key':key,'month':m['month'],'status':'missing_or_ambiguous','matches':len(m['matches'])});continue
  tab=m['matches'][0];name=key+'-'+m['month']+'.json';p=D/name
  if not p.exists():
   q=urllib.parse.urlencode({'ranges':"'"+tab['title'].replace("'","''")+"'",'includeGridData':'true','fields':'spreadsheetId,sheets(properties,data(startRow,startColumn,rowData(values(userEnteredValue,effectiveValue,formattedValue,effectiveFormat.numberFormat))))'})
   status,data=api_json('GET',f'https://sheets.googleapis.com/v4/spreadsheets/{book["id"]}?'+q,token);assert status==200
   save(name,{'book':key,'spreadsheet_id':book['id'],'captured_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'data':data});time.sleep(1.1)
  doc=json.loads(p.read_text());cells=[]
  for sheet in doc['data']['sheets']:
   assert sheet['properties']['sheetId']==tab['sheetId']
   for grid in sheet.get('data',[]):
    for ri,row in enumerate(grid.get('rowData',[]),grid.get('startRow',0)+1):
     for ci,c in enumerate(row.get('values',[]),grid.get('startColumn',0)+1):
      if not c.get('effectiveValue') and not c.get('formattedValue') and not c.get('userEnteredValue'):continue
      cells.append({'a1':col(ci)+str(ri),'row':ri,'col':ci,**c})
  save(key+'-'+m['month']+'-cells.json',cells)
  errors=[{'a1':c['a1'],'error':c['effectiveValue']['errorValue']} for c in cells if 'errorValue' in c.get('effectiveValue',{})];numeric=[c for c in cells if 'numberValue' in c.get('effectiveValue',{})];formulas=[c for c in cells if 'formulaValue' in c.get('userEnteredValue',{})];strings=[c for c in cells if 'stringValue' in c.get('effectiveValue',{})]
  rec={'key':key,'month':m['month'],'status':'captured','sheet_id':tab['sheetId'],'title':tab['title'],'grid_rows':tab['gridProperties']['rowCount'],'grid_cols':tab['gridProperties']['columnCount'],'used_rows':max((c['row'] for c in cells),default=0),'used_cols':max((c['col'] for c in cells),default=0),'cells':len(cells),'numeric':len(numeric),'nonzero':sum(c['effectiveValue']['numberValue']!=0 for c in numeric),'formulas':len(formulas),'errors':errors,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'strings':len(strings)};rows.append(rec);save(key+'-summary.json',rows)
 print(json.dumps([{k:v for k,v in x.items() if k not in ['errors','sha256']}|{'errors':len(x.get('errors',[]))} for x in rows],ensure_ascii=False))
if sys.argv[1]=='metadata':metadata()
else:capture(sys.argv[1])
