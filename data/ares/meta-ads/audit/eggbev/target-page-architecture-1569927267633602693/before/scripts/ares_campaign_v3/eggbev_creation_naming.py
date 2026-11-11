"""Eggbev three-account creation names; metadata only, never a Meta writer."""
from __future__ import annotations
import fcntl,hashlib,json,os,re,tempfile
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import parse_qs
ROOT=Path('/root/mgs-agent')
POLICY_PATH=ROOT/'data/ares/meta-ads/policies/eggbev-us-en-global-creation-naming.json'
NAME_RE=re.compile(r'^(\d+) - (.+) - ENG - US - \((pg_[0-9]+)\) - C([0-9]{2,})$')
class NamingError(ValueError):pass
def load_policy(path=POLICY_PATH):
 p=json.loads(Path(path).read_text())
 if p.get('status')!='active' or len(set(p.get('account_ids',[])))!=3 or p.get('minimum_global_number')!=300:raise NamingError('global naming policy unavailable')
 return p
def stamp(value):return datetime.fromisoformat(str(value).replace('Z','+00:00'))
def applies(created_at,account_id,policy=None):
 p=policy or load_policy();return str(account_id) in p['account_ids'] and stamp(created_at)>=stamp(p['effective_at'])
def format_name(number,page_name,page_token,page_sequence):
 if not isinstance(number,int) or number<300 or not isinstance(page_sequence,int) or page_sequence<1 or re.fullmatch(r'pg_[0-9]+',str(page_token)) is None:raise NamingError('invalid naming identity')
 if not isinstance(page_name,str) or not page_name.strip() or page_name!=page_name.strip() or any(c in page_name for c in '\r\n\t'):raise NamingError('exact Page name required')
 return f'{number} - {page_name} - ENG - US - ({page_token}) - C{page_sequence:02d}'
def reconcile_page(sb_rows,meta_page,page_token):
 if re.fullmatch(r'pg_[0-9]+',str(page_token)) is None:raise NamingError('exact pg token required')
 rows=[r for r in sb_rows if str(r.get('UTM_CAMPAIGN',''))==page_token]
 if len(rows)!=1:raise NamingError('Smart Bidding Page mapping missing or ambiguous')
 r=rows[0];page_id=str(r.get('FB_PAGE_ID',''));name=r.get('PAGE_NAME')
 if not page_id.isdigit() or not isinstance(name,str) or str(meta_page.get('id'))!=page_id or meta_page.get('name')!=name:raise NamingError('Smart Bidding and Meta Page identity mismatch')
 return {'page_token':page_token,'page_id':page_id,'page_name':name}
def collect_history(meta,token,policy=None):
 p=policy or load_policy();snapshots={}
 for aid in p['account_ids']:
  code,account,_=meta.graph_get('act_'+aid,token,{'fields':'id,name,currency,timezone_name,account_status'})
  if code!=200 or account.get('id')!='act_'+aid:raise NamingError('exact account history reader unavailable')
  rows=[];after=None
  for _ in range(100):
   params={'fields':'id,name,status,created_time','limit':200}
   if after:params['after']=after
   code,body,_=meta.graph_get('act_'+aid+'/campaigns',token,params)
   if code!=200 or not isinstance(body.get('data'),list):raise NamingError('account history incomplete')
   rows.extend(body['data']);paging=body.get('paging') or {};cursor=(paging.get('cursors') or {}).get('after')
   if not paging.get('next'):break
   if not cursor or cursor==after:raise NamingError('account history cursor invalid')
   after=cursor
  else:raise NamingError('account history pagination bound exceeded')
  snapshots[aid]={'account':account,'campaigns':rows,'complete':True,'read_at':datetime.now(timezone.utc).isoformat()}
 return snapshots
def _validate_snapshots(snapshots,policy,now):
 if set(snapshots)!=set(policy['account_ids']):raise NamingError('all three account histories required')
 for aid,s in snapshots.items():
  if s.get('complete') is not True or s.get('account',{}).get('id')!='act_'+aid or not isinstance(s.get('campaigns'),list):raise NamingError('history account identity incomplete')
  age=(now-stamp(s['read_at'])).total_seconds()
  if age< -30 or age>policy['history_freshness_seconds']:raise NamingError('history stale')
def plan_numbers(page_token,count,snapshots,ledger,*,policy=None,now=None):
 p=policy or load_policy();now=now or datetime.now(timezone.utc);_validate_snapshots(snapshots,p,now)
 if not isinstance(count,int) or not 1<=count<=100 or re.fullmatch(r'pg_[0-9]+',page_token) is None:raise NamingError('invalid allocation request')
 global_numbers=[p['minimum_global_number']-1];local_numbers=[0]
 for s in snapshots.values():
  for row in s['campaigns']:
   if row.get('status') in ['DELETED','ARCHIVED']:continue
   name=str(row.get('name',''));prefix=re.match(r'^\s*([0-9]+)\s*-',name)
   if prefix:global_numbers.append(int(prefix.group(1)))
   local=re.search(r'\('+re.escape(page_token)+r'\).*?\bC([0-9]+)\b',name)
   if local:local_numbers.append(int(local.group(1)))
 for row in ledger.get('allocations',{}).values():
  global_numbers.extend(row['global_numbers'])
  if row['page_token']==page_token:local_numbers.extend(row['page_sequences'])
 start=max(global_numbers)+1;local=max(local_numbers)+1
 return list(range(start,start+count)),list(range(local,local+count))
def reserve(request_id,account_id,identity,count,snapshots,*,policy=None,ledger_path=None):
 p=policy or load_policy();path=Path(ledger_path or ROOT/p['ledger_path'])
 if str(account_id) not in p['account_ids'] or not request_id:raise NamingError('request outside naming group')
 # Validate evidence before any local allocation, including replay.
 _validate_snapshots(snapshots,p,datetime.now(timezone.utc));format_name(300,identity['page_name'],identity['page_token'],1)
 if not str(identity.get('page_id','')).isdigit():raise NamingError('Page ID required')
 path.parent.mkdir(parents=True,exist_ok=True)
 with path.with_suffix(path.suffix+'.lock').open('a+') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX);ledger=json.loads(path.read_text()) if path.exists() else {'schema_version':1,'allocations':{}}
  prior=ledger['allocations'].get(request_id)
  if prior:
   if any(prior.get(k)!=v for k,v in {'account_id':str(account_id),'count':count,**identity}.items()):raise NamingError('request naming allocation conflict')
   return prior
  numbers,locals_=plan_numbers(identity['page_token'],count,snapshots,ledger,policy=p)
  row={'request_id':request_id,'account_id':str(account_id),'count':count,**identity,'global_numbers':numbers,'page_sequences':locals_,'names':[format_name(n,identity['page_name'],identity['page_token'],c) for n,c in zip(numbers,locals_)],'status':'RESERVED','reserved_at':datetime.now(timezone.utc).isoformat(),'history_digests':{aid:hashlib.sha256(json.dumps(s,sort_keys=True).encode()).hexdigest() for aid,s in snapshots.items()}}
  ledger['allocations'][request_id]=row;fd,tmp=tempfile.mkstemp(prefix='.eggbev-numbers-',dir=path.parent);os.fchmod(fd,0o600)
  with os.fdopen(fd,'w') as f:json.dump(ledger,f,ensure_ascii=False,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
  os.replace(tmp,path);return row
def allocation(request_id,policy=None):
 p=policy or load_policy();path=ROOT/p['ledger_path'];ledger=json.loads(path.read_text()) if path.exists() else {};return ledger.get('allocations',{}).get(request_id)
def verify_live_reservation(request_id,snapshots,policy=None):
 p=policy or load_policy();_validate_snapshots(snapshots,p,datetime.now(timezone.utc));row=allocation(request_id,p)
 if not row:raise NamingError('request reservation missing')
 expected=dict(zip(row['global_numbers'],row['names']))
 for aid,s in snapshots.items():
  for campaign in s['campaigns']:
   if campaign.get('status') in ['DELETED','ARCHIVED']:continue
   match=re.match(r'^\s*([0-9]+)\s*-',str(campaign.get('name','')))
   if match and int(match.group(1)) in expected and (aid!=row['account_id'] or campaign['name']!=expected[int(match.group(1))]):raise NamingError('global campaign number collision before write')
 return True

def validate_manifest(manifest,policy=None):
 p=policy or load_policy()
 relevant=[c for c in manifest.campaigns if c.mode==p['mode'] and applies(manifest.created_at,c.account_id,p)]
 if not relevant:return
 row=allocation(manifest.request_id,p)
 if not row or len(relevant)!=row['count']:raise NamingError('real request atomic naming reservation required')
 for index,c in enumerate(relevant):
  if c.account_id!=row['account_id'] or c.name!=row['names'][index] or c.adset_name!=p['adset_name']:raise NamingError('campaign or ADGROUP naming does not match reservation')
  if str(c.adset_create.get('promoted_object',{}).get('page_id'))!=row['page_id']:raise NamingError('adset Page does not match pg mapping')
  for ad in c.ads:
   payload=ad.creative_payload
   if str(payload.get('object_story_spec',{}).get('page_id'))!=row['page_id'] or parse_qs(payload.get('url_tags',''),keep_blank_values=True).get('utm_campaign')!=[row['page_token']]:raise NamingError('Page pg and utm_campaign must remain aligned')
