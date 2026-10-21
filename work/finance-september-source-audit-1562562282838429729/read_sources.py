import sys,json,os,time,hashlib
from pathlib import Path
from urllib.parse import urlencode
sys.path.insert(0,'/root/mgs-agent/scripts')
import mgs_google_workspace_auth as g
P=Path(__file__).parent
os.umask(0o077)
g.load_env()
sa=g.load_service_account()
assert sa['client_email']=='mgsagent@mgs-core-prod.iam.gserviceaccount.com' and sa['project_id']=='mgs-core-prod'
token=g.service_account_access_token()
for month in sys.argv[1:] or ['september','august']:
 meta=json.loads((P/(month+'-metadata.json')).read_text())
 sid=meta['sheets']['spreadsheetId']
 manifest=[]
 for sh in meta['sheets']['sheets']:
  prop=sh['properties']; title=prop['title']
  params=urlencode({'ranges':"'"+title.replace("'","''")+"'",'fields':'sheets(properties,data(startRow,startColumn,rowData(values(userEnteredValue,effectiveValue,formattedValue,effectiveFormat(numberFormat)))))'})
  for attempt in range(3):
   status,data=g.api_json('GET',f'https://sheets.googleapis.com/v4/spreadsheets/{sid}?'+params,token,quota_project='mgs-core-prod')
   if status==200:break
   print(json.dumps({'read_failure':title,'http':status,'attempt':attempt+1,'error':data.get('error',{}).get('status')}),flush=True); time.sleep(3*(attempt+1))
  assert status==200,(title,status)
  raw=json.dumps(data,ensure_ascii=False,separators=(',',':')).encode()
  path=P/f'{month}-{prop["sheetId"]}.json'; path.write_bytes(raw)
  rows=data['sheets'][0].get('data',[{}])[0].get('rowData',[])
  nonempty=[(i+1,[c.get('formattedValue','') for c in r.get('values',[])]) for i,r in enumerate(rows) if any(c.get('effectiveValue') or c.get('userEnteredValue') for c in r.get('values',[]))]
  rec={'title':title,'sheetId':prop['sheetId'],'populated_rows':len(nonempty),'last_row':nonempty[-1][0] if nonempty else 0,'sha256':hashlib.sha256(raw).hexdigest()}
  manifest.append(rec)
  print(json.dumps({**rec,'first_rows':nonempty[:4],'last_rows':nonempty[-3:]},ensure_ascii=False),flush=True)
 (P/(month+'-manifest.json')).write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
