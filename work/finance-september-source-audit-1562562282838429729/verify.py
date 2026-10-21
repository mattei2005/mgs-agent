import json,sys,hashlib,datetime
from pathlib import Path
from urllib.parse import urlencode
sys.path.insert(0,'/root/mgs-agent/scripts')
import mgs_google_workspace_auth as g
P=Path(__file__).parent
token=g.service_account_access_token()
receipt={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'checks':[]}
for month in ['september','august']:
 meta=json.loads((P/(month+'-metadata.json')).read_text())['sheets']; sid=meta['spreadsheetId']
 for mode in ['FORMULA','UNFORMATTED_VALUE']:
  params=[('ranges',"'"+s['properties']['title'].replace("'","''")+"'") for s in meta['sheets']]+[('valueRenderOption',mode),('dateTimeRenderOption','SERIAL_NUMBER')]
  status,data=g.api_json('GET',f'https://sheets.googleapis.com/v4/spreadsheets/{sid}/values:batchGet?'+urlencode(params),token,quota_project='mgs-core-prod')
  assert status==200,(month,mode,status)
  (P/f'{month}-readback-{mode}.json').write_text(json.dumps(data,ensure_ascii=False))
  assert len(data['valueRanges'])==len(meta['sheets'])
  for s,vr in zip(meta['sheets'],data['valueRanges']):
   props=s['properties'];orig=json.loads((P/f'{month}-{props["sheetId"]}.json').read_text())['sheets'][0]
   expected={};got={}
   for i,row in enumerate(orig['data'][0].get('rowData',[])):
    for j,c in enumerate(row.get('values',[])):
     ev=c.get('effectiveValue',{});value=ev.get('numberValue',ev.get('stringValue',ev.get('boolValue','')))
     if mode=='FORMULA' and 'formulaValue' in c.get('userEnteredValue',{}):value=c['userEnteredValue']['formulaValue']
     if value!='':expected[(i,j)]=value
   for i,row in enumerate(vr.get('values',[])):
    for j,value in enumerate(row):
     if value!='':got[(i,j)]=value
   differences=[{'row':k[0]+1,'column':k[1]+1,'before':expected.get(k),'now':got.get(k)} for k in set(expected)|set(got) if expected.get(k)!=got.get(k)]
   receipt['checks'].append({'month':month,'tab':props['title'],'mode':mode,'cells':len(expected),'diff_count':len(differences),'differences':differences[:10]})
receipt['pass']=all(c['diff_count']==0 for c in receipt['checks'])
(P/'source-readback-receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2))
print(json.dumps(receipt,ensure_ascii=False));assert receipt['pass']
