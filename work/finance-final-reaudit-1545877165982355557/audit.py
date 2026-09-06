import sys, json, os, re, hashlib, time
from pathlib import Path
from urllib.parse import urlencode
from datetime import datetime, timezone
sys.path.insert(0,'/root/mgs-agent/scripts')
import mgs_google_workspace_auth as auth
ROOT=Path(__file__).parent
IDS={'principal':'16umGPmLukDGQtCEBh2inYLnE9xcqWbHa3gJCM9HG9ak','kelly':'1huhZFlFVEKmY11fR5DxgCWE2TNC3gvw_eXlW2jylVfs','isliago':'1xi7dx-eS678Zy4j3hoJvXedWY1Mnhhvo7jT_hkFqA2c','george':'1cFPIlC2NxRG6GQiF4VmbNqRz09ZWkZXWUzP7nINK9vU','nicolas':'128fEDdXayhgGGKMdLPf-FTWyJRW8-v6JgHzmUSrsOMU','joe':'1syOKCRi-2wpHQNY5fHMcOzjj73EXmFIUbTF1sTIARvQ'}
TOKEN=None

def get(url):
 global TOKEN
 if TOKEN is None:
  auth.load_env()
  for key in ['ARES_DRIVE_AUTH_MODE','MGS_DRIVE_AUTH_PRIMARY','MGS_GOOGLE_SHEETS_AUTH_MODE','MGS_META_APP_ROLES_GOOGLE_AUTH_MODE']:
   assert os.environ.get(key)=='service_account', key+' not canonical'
  sa=auth.load_service_account()
  assert sa['project_id']=='mgs-core-prod' and sa['client_email']=='mgsagent@mgs-core-prod.iam.gserviceaccount.com'
  TOKEN=auth.service_account_access_token()
 for attempt in range(3):
  status,data=auth.api_json('GET',url,TOKEN,quota_project='mgs-core-prod')
  if status==200:return data
  if status not in (0,429,500,502,503):raise RuntimeError(str((status,data.get('error',{}).get('status'))))
  time.sleep(2**attempt)
 raise RuntimeError('GET failed '+str(status))

def save(name,data):
 p=ROOT/name;p.write_text(json.dumps(data,ensure_ascii=False))
 return hashlib.sha256(p.read_bytes()).hexdigest()

def col(n):
 s=''
 while n:n,r=divmod(n-1,26);s=chr(65+r)+s
 return s

def ci(s):
 n=0
 for c in s.upper():n=n*26+ord(c)-64
 return n

def cells(sheet):
 out={}
 for block in sheet.get('data',[]):
  for r,row in enumerate(block.get('rowData',[]),block.get('startRow',0)+1):
   for c,x in enumerate(row.get('values',[]),block.get('startColumn',0)+1):
    if any(k in x for k in ['userEnteredValue','effectiveValue','formattedValue','note']):out[f'{col(c)}{r}']=x
 return out

def val(x):
 v=x.get('effectiveValue',{})
 return next(iter(v.values()),'')
def formula(x):return x.get('userEnteredValue',{}).get('formulaValue','')
def load(name):return json.loads((ROOT/(name+'.json')).read_text())
def cmap(name,title='Agosto 2026'):
 return cells(next(s for s in load(name)['sheets'] if s['properties']['title']==title))

def capture(names):
 manifest=json.loads((ROOT/'manifest.json').read_text()) if (ROOT/'manifest.json').exists() else {}
 for name in names:
  id=IDS[name]
  drive=get('https://www.googleapis.com/drive/v3/files/'+id+'?'+urlencode({'supportsAllDrives':'true','fields':'id,name,modifiedTime,trashed,capabilities(canEdit)'}))
  meta=get('https://sheets.googleapis.com/v4/spreadsheets/'+id+'?fields=spreadsheetId,properties,sheets.properties,namedRanges')
  titles=['Agosto 2026','CAIXA SINTETICO','BASE_DASH','DASH EXECUTIVO'] if name=='principal' else ['Agosto 2026']
  for t in titles:assert t in [s['properties']['title'] for s in meta['sheets']],(name,t)
  qs=[('ranges',"'"+t.replace("'","''")+"'") for t in titles]+[('includeGridData','true'),('fields','spreadsheetId,properties,sheets(properties,merges,basicFilter,data(startRow,startColumn,rowData(values(userEnteredValue,effectiveValue,formattedValue,note,effectiveFormat.numberFormat)))),namedRanges')]
  snap=get('https://sheets.googleapis.com/v4/spreadsheets/'+id+'?'+urlencode(qs))
  save(name+'-metadata.json',{'drive':drive,'sheets':meta})
  sha=save(name+'.json',snap)
  counts=[]
  for s in snap['sheets']:
   cc=cells(s); ff={a:formula(x) for a,x in cc.items() if formula(x)}
   errors={a:x['effectiveValue']['errorValue'] for a,x in cc.items() if 'errorValue' in x.get('effectiveValue',{})}
   extent=[max([int(re.search(r'\d+',a).group()) for a in cc] or [0]),max([ci(re.match(r'[A-Z]+',a).group()) for a in cc] or [0])]
   counts.append({'title':s['properties']['title'],'grid':s['properties'].get('gridProperties'),'extent':extent,'cells':len(cc),'formulas':len(ff),'errors':errors})
  manifest[name]={'id':id,'sha256':sha,'captured_at':datetime.now(timezone.utc).isoformat(),'tabs':counts}
  save('manifest.json',manifest);print(name,json.dumps(counts,ensure_ascii=False),flush=True)
if __name__=='__main__':capture(sys.argv[1:] or list(IDS))
