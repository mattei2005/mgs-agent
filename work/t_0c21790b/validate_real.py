"""Real read-only validation; refuses any provider write method."""
from pathlib import Path
from unittest.mock import patch
import hashlib,json,sys,time
sys.path.insert(0,'/root/mgs-agent/scripts')
from ares_campaign_v3 import shein_request_queue as q,shein_single_clone as d,shein_decision_wait as dw
base=Path('/root/mgs-agent');out=base/'work/t_0c21790b'
inputs=base/'data/ares/meta-ads/audit/shein/campaigns/intake/shein-1566932068317921331'
common=d._load_common();counts={'logical_gets':0,'http_read_calls':0,'provider_writes':0}
class OnlyReads:
 def get_token_from_1password(self,*a,**k):return common.get_token_from_1password(*a,**k)
 def graph_get(self,*a,**k):
  counts['logical_gets']+=1;counts['http_read_calls']+=1
  return common.graph_get(*a,**k)
 def graph_batch_get(self,token,requests):
  assert all(r.get('method','GET')=='GET' for r in requests)
  counts['logical_gets']+=len(requests);counts['http_read_calls']+=1
  return common.graph_batch_get(token,requests)
 def __getattr__(self,key):
  raise AssertionError('Provider operation outside read-only contract: '+key)
start=time.time();rows=[]
with patch.object(d,'_load_common',return_value=OnlyReads()):
 for number in ['011','010','012','009','008']:
  path=inputs/('c'+number+'.json');request=json.loads(path.read_text())
  deps=q.dependencies(request,request['account'],base)
  assert not deps, (number,deps)
  proof=json.loads((q.root(base)/'queue/source-media'/(request['request_id']+'.json')).read_text())
  historical=proof['historical_json'];source={tuple(x) for x in proof['identities']}
  assert historical
  overlaps={rid:sorted(source & {tuple(x) for x in h['identities']}) for rid,h in historical.items()}
  assert not any(overlaps.values())
  job=json.loads(q.job_path(base,request['request_id']).read_text())
  assert job['request']==request and job['attempts']==0 and (job.get('maintenance_hold') or job.get('dispatch_owner')=='foreground')
  rows.append({'input':str(path),'input_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
   'request_id':request['request_id'],'source_number':request['source_number'],
   'source_campaign_id':proof['source_campaign_id'],'ad_bindings':proof['ad_bindings'],
   'inventory_lineages':proof['reservations_json'],'dependencies':deps,'overlaps':overlaps,
   'receipt':proof,'runner_phase':q.state(base,request['request_id']).get('phase')})
result={'kind':'REAL_READ_ONLY_VALIDATION','observed_at':start,'account_id':'937846586033361',
 'validated_inputs':len(rows),'counts':counts,'rows':rows,'meta_writes':0,'drive_writes':0,'inventory_reservations':0}
q.atomic(out/'real-readonly-validation.json',result)
print(json.dumps({'validated_inputs':len(rows),'counts':counts,'sources':[{'number':r['source_number'],'id':r['source_campaign_id'],'ads':len(r['ad_bindings']),'dependencies':r['dependencies'],'lineages':len(r['inventory_lineages'])} for r in rows]}))
