import sys,json,urllib.parse,pathlib,hashlib,datetime
sys.path.insert(0,'/root/mgs-agent/scripts');from mgs_google_workspace_auth import load_env,load_service_account,service_account_access_token,api_json
load_env();sa=load_service_account();assert sa['client_email']=='mgsagent@mgs-core-prod.iam.gserviceaccount.com' and sa['project_id']=='mgs-core-prod'
scopes=['https://www.googleapis.com/auth/spreadsheets.readonly','https://www.googleapis.com/auth/drive.metadata.readonly'];token=service_account_access_token(scopes);quota='mgs-core-prod';sid='16umGPmLukDGQtCEBh2inYLnE9xcqWbHa3gJCM9HG9ak';D=pathlib.Path('/root/mgs-agent/work/finance-payments-indicators-1547706561210753114');D.mkdir(parents=True,exist_ok=True)
def call(url):
 status,data=api_json('GET',url,token,quota_project=quota);assert status==200,(status,str(data)[:300]);return data
drive=call('https://www.googleapis.com/drive/v3/files/'+sid+'?fields=id,name,mimeType,modifiedTime,trashed,capabilities(canEdit)&supportsAllDrives=true');assert drive['id']==sid and not drive['trashed']
meta=call('https://sheets.googleapis.com/v4/spreadsheets/'+sid+'?fields=spreadsheetId,properties(title,locale,timeZone,autoRecalc),sheets(properties(sheetId,title,index,gridProperties))');july=next(s for s in meta['sheets'] if s['properties']['title']=='Julho 2026')
ranges=["'Julho 2026'!C1:L1","'Julho 2026'!F99:J145"]
def batch(render):
 q=urllib.parse.urlencode([('ranges',r) for r in ranges]+[('majorDimension','ROWS'),('valueRenderOption',render),('dateTimeRenderOption','SERIAL_NUMBER')]);return call('https://sheets.googleapis.com/v4/spreadsheets/'+sid+'/values:batchGet?'+q)
formula=batch('FORMULA');raw=batch('UNFORMATTED_VALUE');formatted=batch('FORMATTED_VALUE')
out={'captured_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'identity':{'client_email':sa['client_email'],'project_id':sa['project_id']},'drive':drive,'spreadsheet':meta['properties'],'sheet':july['properties'],'ranges':ranges,'formula':formula['valueRanges'],'raw':raw['valueRanges'],'formatted':formatted['valueRanges']}
p=D/'july-live-sheet-readback.json';p.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');p.chmod(0o600)
# Extract exact comparison points and row labels.
def matrix(kind,i):return out[kind][i].get('values',[])
f=matrix('formula',1);r=matrix('raw',1);z=matrix('formatted',1)
def cell(row,col):
 ri=row-99;ci=col-6
 return {'formula':f[ri][ci] if ri<len(f) and ci<len(f[ri]) else None,'raw':r[ri][ci] if ri<len(r) and ci<len(r[ri]) else None,'formatted':z[ri][ci] if ri<len(z) and ci<len(z[ri]) else None}
points={a:cell(row,col) for a,row,col in [('F103',103,6),('F129',129,6),('F132',132,6),('H136',136,8),('I136',136,9),('H137',137,8),('I137',137,9),('H143',143,8)]}
for a,x in points.items():assert x['raw'] is not None,a
summary={'pass':True,'drive_can_edit':drive['capabilities']['canEdit'],'sheet_id':july['properties']['sheetId'],'modifiedTime':drive['modifiedTime'],'points':points,'source_file_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'sheet_writes':0}
(D/'july-live-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n');print(json.dumps(summary,ensure_ascii=False))
