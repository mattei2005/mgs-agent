import sys,json,os,hashlib,urllib.parse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0,'/root/mgs-agent/scripts')
from mgs_google_workspace_auth import load_env,load_service_account,service_account_access_token,api_json
W=Path(__file__).parent
S='1HoF7ihPzb0_oQIR5cZ0bsWd2b-_5jsHcKBalFi9HG7g'
load_env()
for k in ['ARES_DRIVE_AUTH_MODE','MGS_DRIVE_AUTH_PRIMARY','MGS_GOOGLE_SHEETS_AUTH_MODE','MGS_META_APP_ROLES_GOOGLE_AUTH_MODE']:assert os.environ.get(k)=='service_account',k
sa=load_service_account();assert sa['project_id']=='mgs-core-prod' and sa['client_email']=='mgsagent@mgs-core-prod.iam.gserviceaccount.com'
t=service_account_access_token()
def get(url):
 status,data=api_json('GET',url,t);assert status==200,(status,data.get('error',{}));return data
def save(n,d):
 p=W/n;p.write_text(json.dumps(d,ensure_ascii=False,indent=2));return hashlib.sha256(p.read_bytes()).hexdigest()
d=get(f'https://www.googleapis.com/drive/v3/files/{S}?supportsAllDrives=true&fields=id,name,mimeType,modifiedTime,capabilities,driveId');save('drive.json',d);assert d['capabilities']['canEdit']
m=get(f'https://sheets.googleapis.com/v4/spreadsheets/{S}?fields=spreadsheetId,properties,sheets.properties');save('metadata.json',m)
def fetch(s):
 p=s['properties'];rng=urllib.parse.quote("'"+p['title'].replace("'","''")+"'",safe='')
 for mode in ['UNFORMATTED_VALUE','FORMATTED_VALUE','FORMULA']:
  d=get(f'https://sheets.googleapis.com/v4/spreadsheets/{S}/values/{rng}?valueRenderOption={mode}&dateTimeRenderOption=SERIAL_NUMBER');save(str(p['sheetId'])+'-'+mode+'.json',d)
 return {**p,'rows_read':len(d.get('values',[]))}
with ThreadPoolExecutor(max_workers=3) as pool: result=list(pool.map(fetch,m['sheets']))
save('manifest.json',result)
print(json.dumps(result,ensure_ascii=False))
