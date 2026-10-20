#!/usr/bin/env python3
"""Fail-closed, local-only Ares ad-account scope check. No credentials/API calls."""
import argparse,json,re,sys
from pathlib import Path
REGISTRY=Path('/root/mgs-agent/data/ares/asset-scope.json')
DENY='Conta fora do escopo operacional autorizado do Ares.'
class ScopeError(ValueError):pass
def load_scope(path=REGISTRY):
 try:data=json.loads(Path(path).read_text())
 except (OSError,ValueError):raise ScopeError('Scope unavailable') from None
 rows=data.get('ad_accounts',[])
 ids=[x.get('account_id') for x in rows if isinstance(x,dict)]
 if data.get('schema_version')!=1 or data.get('status')!='active' or data.get('operational_business_id')!='155263197283282' or not ids or len(ids)!=len(rows) or len(set(ids))!=len(ids) or any(not isinstance(x,str) or not re.fullmatch(r'[0-9]{5,30}',x) for x in ids):raise ScopeError('Scope invalid')
 return data

def allowed_account(value,data):
 raw=str(value)
 if raw.startswith('act_'):raw=raw[4:]
 if not re.fullmatch(r'[0-9]{5,30}',raw):return False
 return any(x['account_id']==raw for x in data['ad_accounts'])

def is_ares_context():
 import os
 if os.environ.get('HERMES_PROFILE')=='ares' or os.environ.get('HERMES_HOME','').rstrip('/')=='/root/.hermes/profiles/ares':return True
 if any(str(v).startswith('/root/.hermes/profiles/ares/') for v in sys.argv):return True
 try:return 'ares-gateway.service' in Path('/proc/self/cgroup').read_text()
 except OSError:return False

def enforce_meta_path(path,params=None):
 if not is_ares_context():return
 params=params or {}
 candidates=[]
 for value in re.findall(r'(?:^|/)act_([^/?]+)',str(path)):
  candidates.append(value)
 for key in ('account_id','ad_account_id'):
  if key in (params or {}):candidates.append(str(params[key]))
 if candidates:
  data=load_scope()
  if any(not allowed_account(v,data) for v in candidates):raise ScopeError(DENY)
 batch=(params or {}).get('batch')
 if batch:
  try:children=json.loads(batch) if isinstance(batch,str) else batch
  except ValueError:raise ScopeError('Batch inválido; operação negada.') from None
  if not isinstance(children,list):raise ScopeError('Batch inválido; operação negada.')
  for child in children:
   if not isinstance(child,dict):raise ScopeError('Batch inválido; operação negada.')
   enforce_meta_path(child.get('relative_url',''))

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['validate','check-account','list-accounts']);p.add_argument('target',nargs='?');p.add_argument('--json',action='store_true');args=p.parse_args()
 try:data=load_scope()
 except ScopeError:print('Escopo Ares indisponível; operação negada.');return 4
 if args.command=='validate':out={'status':'ok','business_id':data['operational_business_id'],'accounts':len(data['ad_accounts']),'domains':len(data['domains'])};code=0
 elif args.command=='list-accounts':out={'business_id':data['operational_business_id'],'ad_accounts':data['ad_accounts']};code=0
 elif allowed_account(args.target,data):out={'allowed':True,'account_id':str(args.target).removeprefix('act_'),'business_id':data['operational_business_id']};code=0
 else:out={'allowed':False,'message':DENY};code=3
 print(json.dumps(out,ensure_ascii=False) if args.json else (out.get('message') or json.dumps(out,ensure_ascii=False)))
 return code
if __name__=='__main__':sys.exit(main())
