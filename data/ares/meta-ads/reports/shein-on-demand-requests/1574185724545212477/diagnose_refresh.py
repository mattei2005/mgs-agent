import importlib.util,json
from pathlib import Path
R=Path(__file__).parent
s=importlib.util.spec_from_file_location('task',R/'intraday.py');a=importlib.util.module_from_spec(s);s.loader.exec_module(a)
r=a.runner();requests=[]
for b in r.bindings:
 for cid in a.d.load(R/b['account_id']/'selected.json'):
  requests.append({'path':cid,'params':{'fields':a.d.CAMP_FIELDS}})
for start in range(0,len(requests),50):
 group=requests[start:start+50]
 st,responses,_=r.meta.graph_batch_get(r.token,group)
 assert st==200 and len(responses)==len(group)
 a.d.save(R/f'refresh-diagnostic-{start}.json',{'responses':responses,'observed_at':a.d.now()})
 bad=[]
 for req,resp in zip(group,responses):
  body=resp['body'];body=json.loads(body) if isinstance(body,str) else body
  if resp['code']!=200:
   e=body.get('error',{});bad.append({'campaign_id':req['path'],'http':resp['code'],'code':e.get('code'),'subcode':e.get('error_subcode'),'type':e.get('type'),'message':e.get('message')})
 print(json.dumps({'batch':start,'size':len(group),'bad':bad},ensure_ascii=False),flush=True)
