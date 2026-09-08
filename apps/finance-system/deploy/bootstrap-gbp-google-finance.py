"""Create dedicated corporate GOOGLEFINANCE source; never edits principal workbook."""
import sys,pathlib,json,time,math
from urllib.parse import urlencode
sys.path.insert(0,'/root/mgs-agent/scripts');from mgs_google_workspace_auth import load_env,service_account_access_token,api_json
R=pathlib.Path(__file__).resolve().parents[1];D=R/'private/usability-1546729477319696405';P=D/'google-finance-quotes.json';DRIVE='0AEwt4Ye690ocUk9PVA';load_env();token=service_account_access_token()
def call(method,url,data=None):
 status,out=api_json(method,url,token,data,quota_project='mgs-core-prod');assert status in [200,201],f'Google source HTTP {status}';return out
meta=call('GET','https://www.googleapis.com/drive/v3/files/'+DRIVE+'?'+urlencode({'supportsAllDrives':'true','fields':'id,driveId,capabilities(canAddChildren)'}));assert meta['capabilities']['canAddChildren']
if P.exists():cfg=json.loads(P.read_text())
else:
 out=call('POST','https://www.googleapis.com/drive/v3/files?supportsAllDrives=true&fields=id,driveId,name',{'name':'MGS Financeiro — Cotações Google Finance','mimeType':'application/vnd.google-apps.spreadsheet','parents':[DRIVE]});assert out['driveId']==DRIVE
 cfg={'spreadsheet_id':out['id'],'drive_id':DRIVE,'range':'A1','key':'principal|Agosto 2026|I1','formula':'=GOOGLEFINANCE("GBPUSD")','periods':['2026-08'],'authorization':'1546729477319696405'};P.write_text(json.dumps(cfg,indent=2));P.chmod(0o600)
id=cfg['spreadsheet_id'];meta=call('GET','https://www.googleapis.com/drive/v3/files/'+id+'?supportsAllDrives=true&fields=id,driveId,trashed,capabilities(canEdit)');assert meta['driveId']==DRIVE and not meta['trashed'] and meta['capabilities']['canEdit']
call('POST','https://sheets.googleapis.com/v4/spreadsheets/'+id+':batchUpdate',{'requests':[{'updateSpreadsheetProperties':{'properties':{'locale':'en_US','timeZone':'America/New_York','autoRecalc':'MINUTE'},'fields':'locale,timeZone,autoRecalc'}}]})
current=call('GET','https://sheets.googleapis.com/v4/spreadsheets/'+id+'/values/A1?valueRenderOption=FORMULA').get('values',[]);assert current in [[],[[cfg['formula']]]],'Unexpected existing quote cell'
if not current:call('PUT','https://sheets.googleapis.com/v4/spreadsheets/'+id+'/values/A1?valueInputOption=USER_ENTERED',{'range':'A1','majorDimension':'ROWS','values':[[cfg['formula']]]})
for attempt in range(5):
 rb=call('GET','https://sheets.googleapis.com/v4/spreadsheets/'+id+'?ranges=A1&includeGridData=true');cell=rb['sheets'][0]['data'][0]['rowData'][0]['values'][0];assert cell['userEnteredValue']['formulaValue']==cfg['formula'];value=cell.get('effectiveValue',{}).get('numberValue')
 if isinstance(value,(int,float)) and math.isfinite(value) and 0<value<10000:break
 time.sleep(2)
else:raise RuntimeError('GOOGLEFINANCE value not ready; retain source and retry')
out={'pass':True,'spreadsheet_id':id,'drive_id':DRIVE,'formula':cfg['formula'],'value':value,'principal_sheet_writes':0};(D/'google-source-readback.json').write_text(json.dumps(out,indent=2));print(json.dumps(out))
