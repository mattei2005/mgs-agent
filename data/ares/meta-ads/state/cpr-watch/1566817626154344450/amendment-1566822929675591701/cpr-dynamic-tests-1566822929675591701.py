import importlib.util,sys,json,copy,tempfile
from pathlib import Path
from unittest.mock import patch
home=Path('/root/.hermes/profiles/ares')
def module(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);sys.modules[n]=m;s.loader.exec_module(m);return m
w=module('dynamic_test_watch',home/'scripts/shein-g004-cpr-watch-20261102.py');x=module('discovery_test',home/'scripts/shein-g004-cpr-watch-20261102-discovery.py')
base={'id':'test234','number':'234','name':'234 - test','account_id':w.AID,'created_time':'2026-11-02T12:00:00-0500','status':'ACTIVE'}
old={**base,'id':'old','created_time':'2026-11-01T23:59:59-0500'};deleted={**base,'id':'deleted','status':'DELETED'};future={**base,'id':'tomorrow','created_time':'2026-11-03T00:00:00-0500'}
assert set(x.candidates([base,old,deleted,future]))=={'test234'}
try:x.candidates([{**base,'account_id':'other'}])
except AssertionError:pass
else:raise AssertionError('Cross-account admitted')
cs=x.candidates([base]);aset={'campaign_id':'test234','optimization_goal':'OFFSITE_CONVERSIONS','promoted_object':{'custom_event_type':'ADD_TO_WISHLIST'}}
existing=[{**base,'id':'existing','number':'229'}]
merged,pending=x.admit(existing,cs,[aset]);assert len(merged)==2 and not pending
merged2,pending=x.admit(merged,cs,[aset]);assert merged2==merged
notready,pending=x.admit(existing,cs,[]);assert notready==existing and len(pending)==1
wrong,pending=x.admit(existing,cs,[{**aset,'optimization_goal':'LINK_CLICKS'}]);assert wrong==existing and len(pending)==1
assert w.decisions({'existing':{'cpr':'2'},'test234':{'cpr':'1.30000001'}},{'existing':True},'1.30')[0]==['test234']
parts=w.split_parts(['line '*20 for _ in range(150)]);assert len(parts)>1 and all(len(p.encode('utf-16-le'))//2<=2000 for p in parts)
# Expiry guard precedes discovery or API, including explicit amendment refresh.
m=w.load(w.ROOT/'manifest.json');expired=copy.deepcopy(m);expired['date']='2026-11-01'
class Args:initial=False;refresh=True;dry_run=False
with patch.object(w,'load',return_value=expired),patch.object(w,'scope',side_effect=AssertionError('expired scope')):
 assert w.execute(Args())=={'status':'EXPIRED','api_calls':0}
print(json.dumps({'status':'PASS','tests':['today_only','prior_day_excluded','terminal_excluded','tomorrow_excluded','cross_account_rejected','future_campaign_admitted','membership_dedup','pending_retried','wrong_event_not_imputed','old_alert_state_preserved','fractional_threshold','multi_part','expired_no_API'],'core':w.self_test(),'external_calls':0}))
