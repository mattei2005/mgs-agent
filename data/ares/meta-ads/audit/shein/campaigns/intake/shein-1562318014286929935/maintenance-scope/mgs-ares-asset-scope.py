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

PROVENANCE=Path('/root/mgs-agent/data/ares/meta-ads/state/scoped-object-provenance.json')
APP_ID='1299247318762949'
OBJECT_EDGES={'campaigns':'campaign','adsets':'adset','ads':'ad','adcreatives':'creative','advideos':'video','videos':'video','adspixels':'pixel'}
BLOCKED_DISCOVERY={'adaccounts','businesses','owned_ad_accounts','client_ad_accounts','owned_pages','client_pages','assigned_users'}

def _request_parts(path,params):
 from urllib.parse import urlsplit,parse_qs,unquote
 raw=str(path)
 parsed=urlsplit(raw)
 if parsed.scheme or parsed.netloc or parsed.fragment or '\\' in raw:raise ScopeError(DENY)
 clean=unquote(parsed.path).strip('/')
 if any(x in {'.','..'} for x in clean.split('/')) or '{' in clean or '}' in clean:raise ScopeError(DENY)
 query=parse_qs(parsed.query,keep_blank_values=True)
 if any(len(v)!=1 for v in query.values()):raise ScopeError(DENY)
 merged={k:v[0] for k,v in query.items()}
 for k,v in dict(params or {}).items():
  if k in merged and str(merged[k])!=str(v):raise ScopeError(DENY)
  merged[k]=v
 return clean,merged

def _scope_signature(data):
 import hashlib
 return hashlib.sha256(json.dumps(sorted(x['account_id'] for x in data['ad_accounts'])).encode()).hexdigest()

def _objects(data):
 try:stored=json.loads(PROVENANCE.read_text())
 except (OSError,ValueError):return {}
 if stored.get('scope_signature')!=_scope_signature(data):return {}
 return stored.get('objects',{}) if isinstance(stored.get('objects'),dict) else {}

def _account_for_node(node,data):
 if allowed_account(node,data):return node.removeprefix('act_')
 row=_objects(data).get(node,{})
 account=row.get('account_id')
 return account if row.get('source')=='scoped_graph_response' and allowed_account(account,data) else None

def enforce_meta_path(path,params=None,method='GET'):
 if not is_ares_context():return
 clean,params=_request_parts(path,params)
 # The technical app exception is metadata-only and never grants discovery.
 if clean==APP_ID and method.upper()=='GET' and set(str(params.get('fields','id,name')).split(','))<={'id','name'} and set(params)<={'fields'}:return
 data=load_scope()
 # Read-only invoices of the one operational business; never business discovery.
 if clean==data.get('operational_business_id','')+'/business_invoices':
  invoice_fields={'id','invoice_id','ad_account_ids','amount','currency','billing_period','invoice_date','payment_status','invoice_type','due_date'}
  requested=set(str(params.get('fields','')).split(','))
  permitted={'fields','issue_start_date','issue_end_date','start_date','end_date','after','before','limit'}
  if method.upper()!='GET' or not requested or 'ad_account_ids' not in requested or not requested.issubset(invoice_fields) or not set(params).issubset(permitted):raise ScopeError(DENY)
  return
 for key in ('account_id','ad_account_id'):
  if key in params and not allowed_account(params[key],data):raise ScopeError(DENY)
 batch=params.get('batch')
 if batch is not None:
  if clean:raise ScopeError(DENY)
  try:children=json.loads(batch) if isinstance(batch,str) else batch
  except (ValueError,TypeError):raise ScopeError(DENY) from None
  if not isinstance(children,list) or not children or len(children)>50:raise ScopeError(DENY)
  from urllib.parse import parse_qs
  for child in children:
   if not isinstance(child,dict) or not child.get('relative_url'):raise ScopeError(DENY)
   body=child.get('body') or {}
   if isinstance(body,str):
    pairs=parse_qs(body,keep_blank_values=True)
    if any(len(v)!=1 for v in pairs.values()):raise ScopeError(DENY)
    body={k:v[0] for k,v in pairs.items()}
   if not isinstance(body,dict):raise ScopeError(DENY)
   enforce_meta_path(child['relative_url'],body,child.get('method','GET'))
  return
 # Multi-ID parameters must prove every node, even when combined with a path.
 if params.get('ids'):
  ids=params['ids'] if isinstance(params['ids'],list) else str(params['ids']).split(',')
  if not ids:raise ScopeError(DENY)
  for node in ids:enforce_meta_path(str(node),{k:v for k,v in params.items() if k!='ids'},method)
  if not clean:return
 parts=clean.split('/')
 if not parts or not re.fullmatch(r'(?:act_)?[0-9]{5,30}',parts[0]):raise ScopeError(DENY)
 if any(edge in BLOCKED_DISCOVERY for edge in parts[1:]):raise ScopeError(DENY)
 if re.search(r'\b(?:'+ '|'.join(BLOCKED_DISCOVERY)+r')\b',str(params.get('fields',''))):raise ScopeError(DENY)
 # A caller-provided account_id is not proof that a bare object belongs to it.
 if not _account_for_node(parts[0],data):raise ScopeError(DENY)


def observe_meta_response(path,params,payload,method='GET'):
 """Record only IDs obtained through an already validated account/object path."""
 if not is_ares_context() or not isinstance(payload,(dict,list)):return
 enforce_meta_path(path,params,method)
 clean,merged=_request_parts(path,params)
 if merged.get('batch') is not None:
  children=merged['batch'];children=json.loads(children) if isinstance(children,str) else children
  if isinstance(payload,list):
   for child,response in zip(children,payload):
    if isinstance(response,dict) and 200<=int(response.get('code',0))<300:
     body=response.get('body');body=json.loads(body) if isinstance(body,str) else body
     observe_meta_response(child['relative_url'],None,body,child.get('method','GET'))
  return
 data=load_scope()
 if clean==data.get('operational_business_id','')+'/business_invoices':
  invoices=payload.get('data') if isinstance(payload,dict) else None
  if not isinstance(invoices,list):raise ScopeError(DENY)
  for invoice in invoices:
   account_ids=invoice.get('ad_account_ids') if isinstance(invoice,dict) else None
   if not isinstance(account_ids,list) or not account_ids or any(not allowed_account(str(a),data) for a in account_ids):raise ScopeError(DENY)
  return
 parts=clean.split('/');account=_account_for_node(parts[0],data)
 if not account:return
 updates={}
 def collect(row):
  if isinstance(row,list):
   for value in row:collect(value)
  elif isinstance(row,dict):
   business=row.get('business')
   if isinstance(business,dict) and business.get('id') is not None and str(business['id'])!=data['operational_business_id']:raise ScopeError(DENY)
   if row.get('account_id') is not None and not allowed_account(str(row['account_id']),data):raise ScopeError(DENY)
   if row.get('account_id') is not None and str(row['account_id']).removeprefix('act_')!=account:raise ScopeError(DENY)
   oid=str(row.get('id',''))
   if re.fullmatch(r'[0-9]{5,30}',oid):updates[oid]={'account_id':account,'source':'scoped_graph_response'}
   for key in ('data','campaigns','adsets','ads','creative','adcreatives','videos','advideos','adspixels'):
    if isinstance(row.get(key),(dict,list)):collect(row[key])
 collect(payload)
 if not updates:return
 import fcntl,os,tempfile
 PROVENANCE.parent.mkdir(parents=True,exist_ok=True)
 with Path(str(PROVENANCE)+'.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX)
  objects=_objects(data)
  for oid,row in updates.items():
   if oid in objects and objects[oid].get('account_id')!=row['account_id']:raise ScopeError(DENY)
  objects.update(updates)
  fd,name=tempfile.mkstemp(prefix='.scoped-provenance-',dir=PROVENANCE.parent)
  os.fchmod(fd,0o600)
  with os.fdopen(fd,'w') as stream:
   json.dump({'schema_version':1,'scope_signature':_scope_signature(data),'objects':objects},stream);stream.flush();os.fsync(stream.fileno())
  os.replace(name,PROVENANCE)

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
