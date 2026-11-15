#!/usr/bin/env python3
"""Read-only exact permission evidence; never change or expand access."""
import importlib.util,json
from pathlib import Path
from datetime import datetime,timezone
s=importlib.util.spec_from_file_location('image_permission_runner','/root/mgs-agent/scripts/ares-eggbev-target-clone.py')
assert s is not None and s.loader is not None
r=importlib.util.module_from_spec(s);s.loader.exec_module(r)
_,m,_,t=r.runtime()
code,issuer,_=m.graph_get_credential_metadata(r.ACCOUNT,t,inspect_token=True);data=issuer.get('data',{})
assert code==200 and str(data.get('user_id'))=='122147293515218951' and str(data.get('app_id'))=='953171080682697' and data.get('type')=='USER'
sc,p,_=m.graph_get('me/permissions',t,{'limit':100})
out={'at':datetime.now(timezone.utc).isoformat(),'actor_id':str(data['user_id']),'app_id':str(data['app_id']),'type':data['type'],'is_valid':data.get('is_valid'),'debug_token_scopes':data.get('scopes',[]),'permissions_http':sc,'permissions':p.get('data',[]),'unread_permissions_pagination':bool(p.get('paging',{}).get('next')),'writes':0}
Path(__file__).with_name('permission-proof.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
