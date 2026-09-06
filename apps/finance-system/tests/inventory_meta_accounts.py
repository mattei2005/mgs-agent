"""Read-only BM inventory and exhaustive Sheet-slot reconciliation; no Meta writes."""
import sys,pathlib,os,json,re,importlib.util,collections,time
ROOT=pathlib.Path(__file__).resolve().parents[1];STATE=ROOT/'private/ui-periods-1546184035921829938';sys.path.insert(0,'/root/mgs-agent/scripts')
from mgs_google_workspace_auth import load_env
load_env();os.environ['ARES_META_TOKEN_CACHE_PATH']='/root/.cache/mgs/finance-bm-inventory-meta-token.json'
sp=importlib.util.spec_from_file_location('meta','/root/mgs-agent/scripts/ares-meta-common.py');meta=importlib.util.module_from_spec(sp);sp.loader.exec_module(meta)
cfg=json.loads(pathlib.Path('/root/mgs-agent/data/ares/meta-ads/accounts/1034081997659047.json').read_text())['accounts'][0];token,_=meta.get_token_from_1password(os.environ.get('FINANCE_META_ITEM') or cfg['token_1password_item']);BM='155263197283282'
accounts={};pages=[]
status,identity,_=meta.graph_get('me',token,{'fields':'id,name'});assert status==200
status,permissions,_=meta.graph_get('me/permissions',token,{'limit':100});assert status==200 and any(p['permission']=='business_management' and p['status']=='granted' for p in permissions.get('data',[]))
status,business,_=meta.graph_get(BM,token,{'fields':'id,name'});assert status==200 and business.get('id')==BM and business.get('name')=='Digital Trust'
(STATE/'meta-selected-identity.json').write_text(json.dumps({'user':identity,'business':business,'business_management_granted':True},ensure_ascii=False,indent=2))
for edge in ['owned_ad_accounts','client_ad_accounts']:
 params={'fields':'id,account_id,name,currency,timezone_name,account_status','limit':100};seen=set()
 while True:
  status,d,h=meta.graph_get(BM+'/'+edge,token,params)
  if status!=200:raise RuntimeError('Meta inventory blocked '+edge+' '+str(status)+' code='+str(d.get('error',{}).get('code')))
  rows=d.get('data',[])
  for a in rows:
   if not re.fullmatch(r'\d+',a['account_id']) or a['id']!='act_'+a['account_id']:raise ValueError('Meta account identity mismatch')
   accounts[a['account_id']]={**a,'business_id':BM}
  pages.append({'edge':edge,'rows':len(rows),'has_more':bool(d.get('paging',{}).get('next'))});(STATE/'meta-accounts-live.json').write_text(json.dumps({'business_id':BM,'accounts':list(accounts.values()),'pages':pages},ensure_ascii=False,indent=2))
  if not d.get('paging',{}).get('next'):break
  cursor=d.get('paging',{}).get('cursors',{}).get('after')
  if not cursor or cursor in seen:raise ValueError('Incomplete pagination')
  seen.add(cursor);params['after']=cursor;time.sleep(.3)
source=json.loads((ROOT/'private/source.json').read_text());model=json.loads((ROOT/'private/ui-model.json').read_text());domain=json.loads((ROOT/'private/domain.json').read_text());lookup={c['id']:c for c in source['cells']};facts={f['id']:f for f in domain['facts']};slots={}
for fid,m in model['facts'].items():
 day=int(fid.rsplit('|',1)[1]);f=facts[fid]
 for key in m['spend']:
  x=model['inputs'][key];book,sheet,cell=key.split('|');co=re.sub(r'\d','',cell);base=int(re.sub(r'\D','',cell))-day+1;sid=f'{book}|{sheet}|{co}|{base}'
  s=slots.setdefault(sid,{'slot_id':sid,'sheet_name':x['label'],'book':book,'currency':x['currency'],'sites':[],'countries':[],'keys':[],'nonzero':False,'state':'pending'})
  s['sites']=list(dict.fromkeys(s['sites']+[f['site']]));s['countries']=list(dict.fromkeys(s['countries']+[f['country']]));s['keys']=list(dict.fromkeys(s['keys']+[key]));s['nonzero']=s['nonzero'] or str(x.get('value','')) not in ('','0','0.0','None')
def norm(name):return re.sub(r'[\s·\-–—]+','-',str(name).casefold()).strip('-')
byname=collections.defaultdict(list)
for a in accounts.values():byname[norm(a['name'])].append(a)
registered={}
for s in slots.values():
 name=s['sheet_name'];generic=bool(re.fullmatch(r'[A-Za-z]{2}(?:-[A-Za-z]{2,8}){0,2}|Conta de anúncio|GASTOS',name,re.I));full=byname.get(norm(name),[]);short=re.sub(r'\s*\([^)]*\)\s*$','',name.rstrip(' ·')).strip(' ·');matches=full or byname.get(norm(short),[]) if not generic else []
 s['candidates']=[a['account_id'] for a in matches]
 if generic:s['state']='unnamed_slot'
 elif 'google ads' in name.lower():s['state']='non_meta'
 elif len(matches)==1 and matches[0]['currency']==s['currency']:
  a=matches[0];s.update(state='matched',account_id=a['account_id'],match_rule='normalized_exact' if full else 'explicit_parenthetical_annotation_removed')
  r=registered.setdefault(a['account_id'],{'id':a['account_id'],'name':a['name'],'currency':a['currency'],'business_id':BM,'meta_status':a['account_status'],'timezone':a['timezone_name'],'verified':True,'sites':[],'source_links':[],'source_names':[]})
  for k in ['sites']:r[k]=list(dict.fromkeys(r[k]+s[k]))
  r['source_links']=list(dict.fromkeys(r['source_links']+s['keys']));r['source_names']=list(dict.fromkeys(r['source_names']+[name]))
 elif len(matches)>1:s['state']='ambiguous_name'
 elif matches:s['state']='currency_conflict'
 else:s['state']='not_found'
summary={'business_id':BM,'meta_accounts':len(accounts),'source_slots':len(slots),'states':dict(collections.Counter(s['state'] for s in slots.values())),'matched_account_ids':len(registered),'meta_writes':0}
(STATE/'account-slot-checklist.json').write_text(json.dumps(list(slots.values()),ensure_ascii=False,indent=2));(STATE/'accounts-to-register.json').write_text(json.dumps(list(registered.values()),ensure_ascii=False,indent=2));(STATE/'account-reconciliation.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary));print(json.dumps({'unresolved_named':[{'name':s['sheet_name'],'sites':s['sites'],'state':s['state']} for s in slots.values() if s['state'] not in ('matched','unnamed_slot')]},ensure_ascii=False))
