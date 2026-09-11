import sys,json,pathlib,urllib.parse,datetime,hashlib,re
sys.path.insert(0,'/root/mgs-agent/scripts');from mgs_google_workspace_auth import load_env,load_service_account,service_account_access_token,api_json
load_env();sa=load_service_account();assert sa['client_email']=='mgsagent@mgs-core-prod.iam.gserviceaccount.com' and sa['project_id']=='mgs-core-prod';token=service_account_access_token();root=pathlib.Path('/root/mgs-agent/work/adops-revenue-1547811852405178460');meta=json.loads((root/'preflight.json').read_text());summary={}
for network,f in meta['files'].items():
 ranges=[x['title'] for x in f['tabs']];responses={}
 for mode in ['UNFORMATTED_VALUE','FORMATTED_VALUE','FORMULA']:
  params=[('ranges',"'"+x.replace("'","''")+"'") for x in ranges]+[('valueRenderOption',mode),('dateTimeRenderOption','FORMATTED_STRING')];status,data=api_json('GET','https://sheets.googleapis.com/v4/spreadsheets/'+f['id']+'/values:batchGet?'+urllib.parse.urlencode(params),token,quota_project='mgs-core-prod');assert status==200 and len(data['valueRanges'])==len(ranges);responses[mode]=data
  payload=json.dumps(data,ensure_ascii=False,sort_keys=True).encode();(root/(network+'-'+mode.lower()+'.json')).write_bytes(payload);(root/(network+'-'+mode.lower()+'.sha256')).write_text(hashlib.sha256(payload).hexdigest()+'\n')
 rows=[]
 for i,title in enumerate(ranges):
  values=responses['UNFORMATTED_VALUE']['valueRanges'][i].get('values',[]);formatted=responses['FORMATTED_VALUE']['valueRanges'][i].get('values',[]);formulas=responses['FORMULA']['valueRanges'][i].get('values',[]);maxcols=max([len(x) for x in values] or [0]);formula_cells=sum(isinstance(v,str) and v.startswith('=') for r in formulas for v in r);rows.append({'title':title,'rows':len(values),'max_columns':maxcols,'formula_cells':formula_cells,'first_rows':formatted[:4],'last_rows':formatted[-3:]})
 summary[network]=rows
out={'pass':True,'captured_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'identity':sa['client_email'],'sheet_writes':0,'summary':summary};(root/'capture-summary.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(json.dumps(out,ensure_ascii=False))
