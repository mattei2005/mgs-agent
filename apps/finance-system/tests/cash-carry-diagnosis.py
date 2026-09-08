"""Read-only exact cash-carry diagnosis after Rodolfo mid-turn correction."""
import sys,pathlib,json,urllib.parse,datetime
sys.path.insert(0,'/root/mgs-agent/scripts');from mgs_google_workspace_auth import load_env,load_service_account,service_account_access_token,api_json
load_env();sa=load_service_account();assert sa['client_email']=='mgsagent@mgs-core-prod.iam.gserviceaccount.com';token=service_account_access_token();sid='16umGPmLukDGQtCEBh2inYLnE9xcqWbHa3gJCM9HG9ak';D=pathlib.Path('/root/mgs-agent/apps/finance-system/private/manager-access-1546858367635685396')
def get(url):
 status,d=api_json('GET',url,token);assert status==200,(status,str(d)[:500]);return d
meta=get('https://www.googleapis.com/drive/v3/files/'+sid+'?supportsAllDrives=true&fields=id,name,modifiedTime,capabilities');sheetmeta=get('https://sheets.googleapis.com/v4/spreadsheets/'+sid+'?fields=spreadsheetId,sheets.properties')
ranges=["'"+name+" 2026'!A99:O160" for name in ['Abril','Maio','Junho','Julho','Agosto']]+["'Abril 2026'!Q17:AC36","'CAIXA SINTETICO'!C1:J82"]
q=urllib.parse.urlencode([('ranges',r) for r in ranges]+[('includeGridData','true'),('fields','spreadsheetId,sheets(properties,data(startRow,startColumn,rowData(values(userEnteredValue,effectiveValue,formattedValue))))')]);data=get('https://sheets.googleapis.com/v4/spreadsheets/'+sid+'?'+q)
def col(n):
 out=''
 while n:n,k=divmod(n-1,26);out=chr(65+k)+out
 return out
out={}
for sheet in data['sheets']:
 cells={}
 for grid in sheet.get('data',[]):
  for ri,row in enumerate(grid.get('rowData',[]),grid.get('startRow',0)+1):
   for ci,c in enumerate(row.get('values',[]),grid.get('startColumn',0)+1):
    if c:cells[col(ci)+str(ri)]=c
 out[sheet['properties']['title']]=cells
p=D/'cash-carry-live.json';p.write_text(json.dumps({'captured_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'drive':meta,'cells':out},ensure_ascii=False,indent=2));p.chmod(0o600)
for month,cells in out.items():
 if month=='CAIXA SINTETICO':continue
 print(month,json.dumps({k:v for k,v in cells.items() if k in ['S19','G129','G137','G138','G139','G140','G141','G142','G143','H129','F129','E129']},ensure_ascii=False))
