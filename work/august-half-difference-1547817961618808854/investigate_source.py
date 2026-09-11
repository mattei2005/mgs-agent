import sys,json,pathlib,urllib.parse,datetime,re
sys.path.insert(0,'/root/mgs-agent/scripts');from mgs_google_workspace_auth import load_env,load_service_account,service_account_access_token,api_json
load_env();sa=load_service_account();assert sa['client_email']=='mgsagent@mgs-core-prod.iam.gserviceaccount.com' and sa['project_id']=='mgs-core-prod';token=service_account_access_token();sid='16umGPmLukDGQtCEBh2inYLnE9xcqWbHa3gJCM9HG9ak';sheet='Agosto 2026';root=pathlib.Path('/root/mgs-agent/work/august-half-difference-1547817961618808854');root.mkdir(parents=True,exist_ok=True,mode=0o700)
def col(n):
 s=''
 while n:n,r=divmod(n-1,26);s=chr(65+r)+s
 return s
responses={}
for mode in ['FORMULA','UNFORMATTED_VALUE','FORMATTED_VALUE']:
 url='https://sheets.googleapis.com/v4/spreadsheets/'+sid+'/values/'+urllib.parse.quote("'"+sheet+"'",safe='')+'?'+urllib.parse.urlencode({'valueRenderOption':mode,'dateTimeRenderOption':'FORMATTED_STRING'});status,data=api_json('GET',url,token,quota_project='mgs-core-prod');assert status==200;responses[mode]=data.get('values',[]);(root/(mode.lower()+'.json')).write_text(json.dumps(data,ensure_ascii=False)+'\n')
rows=max(map(len,responses.values()));cols=max((len(r) for grid in responses.values() for r in grid),default=0);hits=[];labels=[]
for ri in range(rows):
 for ci in range(max(len(responses['UNFORMATTED_VALUE'][ri]) if ri<len(responses['UNFORMATTED_VALUE']) else 0,len(responses['FORMATTED_VALUE'][ri]) if ri<len(responses['FORMATTED_VALUE']) else 0)):
  u=responses['UNFORMATTED_VALUE'][ri][ci] if ri<len(responses['UNFORMATTED_VALUE']) and ci<len(responses['UNFORMATTED_VALUE'][ri]) else None;f=responses['FORMATTED_VALUE'][ri][ci] if ri<len(responses['FORMATTED_VALUE']) and ci<len(responses['FORMATTED_VALUE'][ri]) else ''
  if isinstance(u,(int,float)) and abs(float(u)-17701.42)<20:hits.append({'cell':col(ci+1)+str(ri+1),'raw':u,'formatted':f,'formula':responses['FORMULA'][ri][ci] if ri<len(responses['FORMULA']) and ci<len(responses['FORMULA'][ri]) else None})
  if isinstance(f,str) and '50%' in f:labels.append({'cell':col(ci+1)+str(ri+1),'formatted':f})
contexts=[]
for hit in hits:
 m=re.fullmatch(r'([A-Z]+)(\d+)',hit['cell']);row=int(m.group(2));ci=0
 for ch in m.group(1):ci=ci*26+ord(ch)-64
 contexts.append({'hit':hit,'row_formatted':{col(c):responses['FORMATTED_VALUE'][row-1][c-1] if row-1<len(responses['FORMATTED_VALUE']) and c-1<len(responses['FORMATTED_VALUE'][row-1]) else None for c in range(max(1,ci-5),ci+6)},'row_formula':{col(c):responses['FORMULA'][row-1][c-1] if row-1<len(responses['FORMULA']) and c-1<len(responses['FORMULA'][row-1]) else None for c in range(max(1,ci-5),ci+6)}})
out={'pass':True,'captured_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'identity':sa['client_email'],'sheet':sheet,'rows':rows,'columns':cols,'hits':hits,'labels_50':labels,'contexts':contexts,'sheet_writes':0};(root/'source-readback.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'pass':True,'hits':hits,'labels_50':labels,'contexts':contexts,'sheet_writes':0},ensure_ascii=False))
