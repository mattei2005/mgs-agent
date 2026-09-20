import sys,json,hashlib,urllib.parse
from pathlib import Path
sys.path.insert(0,'/root/mgs-agent/scripts')
from mgs_google_workspace_auth import service_account_access_token,api_json
W=Path(__file__).parent;sid='1HoF7ihPzb0_oQIR5cZ0bsWd2b-_5jsHcKBalFi9HG7g';t=service_account_access_token();base='https://sheets.googleapis.com/v4/spreadsheets/'+sid
spec={701:('$1,419,47',1419.47),914:('$1,309,12',1309.12),1893:('$1,144,90',1144.90),2150:('$1,145,41',1145.41)}
def call(method,url,payload=None):
 code,d=api_json(method,url,t,payload);assert code==200,(code,d);return d
def read():
 return {mode:call('GET',base+'/values/'+urllib.parse.quote("'rede AV - detalhado'!G1:G14421",safe='')+'?valueRenderOption='+mode) for mode in ['FORMULA','UNFORMATTED_VALUE','FORMATTED_VALUE']}
before=read();(W/'source-numbers-before.json').write_text(json.dumps(before));(W/'source-numbers-before.sha256').write_text(hashlib.sha256((W/'source-numbers-before.json').read_bytes()).hexdigest())
for r,(old,new) in spec.items():assert before['UNFORMATTED_VALUE']['values'][r-1][0] in [old,new]
changed=[]
for batch in [[701],[914,1893,2150]]:
 data=[{'range':f"'rede AV - detalhado'!G{r}",'values':[[spec[r][1]]]} for r in batch if before['UNFORMATTED_VALUE']['values'][r-1][0]==spec[r][0]]
 if data:call('POST',base+'/values:batchUpdate',{'valueInputOption':'RAW','data':data});changed+=batch
 after=read()
 for r in batch:assert after['UNFORMATTED_VALUE']['values'][r-1][0]==spec[r][1]
for mode in before:
 for i,(a,b) in enumerate(zip(before[mode]['values'],after[mode]['values']),1):
  if i not in spec:assert a==b,(mode,i,a,b)
(W/'source-numbers-readback.json').write_text(json.dumps(after));print(json.dumps({'pass':True,'numeric_cells_changed':changed,'values':{str(r):after['UNFORMATTED_VALUE']['values'][r-1][0] for r in spec},'untargeted_G_cells_preserved':True}))
