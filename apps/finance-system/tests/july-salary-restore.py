"""Restore ONLY July2026 Jislaine to1500 per Rodolfo1546866505663254599; no August salary write."""
import pathlib,sys,json,urllib.parse,hashlib,datetime
sys.path.insert(0,'/root/mgs-agent/scripts');from mgs_google_workspace_auth import load_env,load_service_account,service_account_access_token,api_json
load_env();assert load_service_account()['client_email']=='mgsagent@mgs-core-prod.iam.gserviceaccount.com';token=service_account_access_token();R=pathlib.Path('/root/mgs-agent/apps/finance-system');D=R/'private/manager-access-1546858367635685396';API='https://sheets.googleapis.com/v4/spreadsheets/16umGPmLukDGQtCEBh2inYLnE9xcqWbHa3gJCM9HG9ak'
def call(method,url,body=None):
 status,d=api_json(method,url,token,body);assert status==200,(status,str(d)[:300]);return d

def get():
 ranges=["'Julho 2026'!A99:O160","'Agosto 2026'!G129","'Agosto 2026'!M155:P160"]
 q=urllib.parse.urlencode([('ranges',r) for r in ranges]+[('includeGridData','true'),('fields','sheets(properties.title,data(startRow,startColumn,rowData(values(userEnteredValue,effectiveValue,formattedValue))))')]);d=call('GET',API+'?'+q);out={}
 for s in d['sheets']:
  cells={}
  for g in s['data']:
   for ri,row in enumerate(g.get('rowData',[]),g.get('startRow',0)+1):
    for ci,c in enumerate(row.get('values',[]),g.get('startColumn',0)+1):
     if c:
      a='';n=ci
      while n:n,k=divmod(n-1,26);a=chr(65+k)+a
      cells[a+str(ri)]=c
  out[s['properties']['title']]=cells
 return out
before=get();p=D/'july-salary-before.json';assert not p.exists();p.write_text(json.dumps(before,ensure_ascii=False,indent=2));p.chmod(0o600);backuphash=hashlib.sha256(p.read_bytes()).hexdigest();j=before['Julho 2026'];assert j['O156']['userEnteredValue']=={'numberValue':-3000} and 'Jislaine' in j['L156']['formattedValue']
q=urllib.parse.quote("'Julho 2026'!O156",safe='');response=call('PUT',API+'/values/'+q+'?valueInputOption=RAW',{'range':"'Julho 2026'!O156",'majorDimension':'ROWS','values':[[-1500]]});assert response['updatedCells']==1
after=get();assert after['Julho 2026']['O156']['userEnteredValue']=={'numberValue':-1500};diff=[]
for name,cells in before.items():
 for a,c in cells.items():
  n=after[name].get(a,{})
  if c.get('userEnteredValue')!=n.get('userEnteredValue'):diff.append((name,a))
assert diff==[('Julho 2026','O156')]
assert abs(after['Julho 2026']['F132']['effectiveValue']['numberValue']-0.7133221368276281)<1e-8;assert after['Agosto 2026']['G129']['effectiveValue']==after['Julho 2026']['F132']['effectiveValue'];assert before['Agosto 2026'].get('P157')==after['Agosto 2026'].get('P157')
(D/'july-salary-after.json').write_text(json.dumps(after,ensure_ascii=False,indent=2));out={'pass':True,'authorization':'1546866505663254599','backup_sha256':backuphash,'source_input_changes':diff,'july_salary_brl':1500,'july_saldo':after['Julho 2026']['F132']['effectiveValue']['numberValue'],'august_g129':after['Agosto 2026']['G129']['effectiveValue']['numberValue'],'august_source_salary_unchanged':True};(D/'july-salary-readback.json').write_text(json.dumps(out,indent=2));print(json.dumps(out))
