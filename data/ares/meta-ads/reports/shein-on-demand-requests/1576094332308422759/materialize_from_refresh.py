import importlib.util,json
from pathlib import Path
R=Path(__file__).parent
s=importlib.util.spec_from_file_location('task',R/'intraday.py');a=importlib.util.module_from_spec(s);s.loader.exec_module(a)
q=a.request();expected={cid for b in q['bindings'] for cid in a.d.load(R/b['account_id']/'selected.json')};found={};stamps=[];by_id_stamp={}
for start in range(0,len(expected),50):
 d=a.d.load(R/f'refresh-diagnostic-{start}.json');stamps.append(d['observed_at'])
 for resp in d['responses']:
  assert resp['code']==200
  obj=resp['body'];obj=json.loads(obj) if isinstance(obj,str) else obj
  assert obj['id'] not in found;found[obj['id']]=obj;by_id_stamp[obj['id']]=d['observed_at']
assert set(found)==expected
for b in q['bindings']:
 p=R/b['account_id'];cm={x['id']:x for x in a.d.load(p/'campaigns.json')}
 for cid in a.d.load(p/'selected.json'):
  obj=found[cid];assert obj['account_id']==b['account_id'] and obj['name']==cm[cid]['name'];cm[cid]=obj
 selected=a.d.load(p/'selected.json');stamp=max((by_id_stamp[cid] for cid in selected),default=max(stamps))
 a.d.save(p/'campaigns.json',list(cm.values()));a.d.save(p/'refresh-observed-at.json',{'observed_at':stamp})
a.render(refresh=False)
