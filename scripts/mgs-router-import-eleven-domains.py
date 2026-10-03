#!/usr/bin/env python3
"""Reconcile/import the exact eleven-domain Keitaro migration; never writes DNS or source."""
import argparse,copy,hashlib,json,os,re,shutil,subprocess,sys
from pathlib import Path
from datetime import datetime,timezone
from fractions import Fraction
from urllib.parse import urlsplit
import requests
BASE=Path('/root/mgs-agent');PANEL='https://route.mgsdigitalcorp.com';APPROVAL='1556013403586306080'
SOURCE=BASE/'data/mgs-router-eleven-domains-keitaro-source.json'
PLAN=BASE/'data/mgs-router-eleven-domains-import-plan.json'
RESULT=BASE/'data/mgs-router-eleven-domains-import-validation.json'
BACKUP=Path('/root/.local/share/mgs-router-rollbacks')/APPROVAL
APEX=['wavesbee.com','zuout.com','dicasfinancas.info','openzed.com','cliquet.com','amazingxjobs.com','eggbev.com','portalrelevante.com','conectageral.com','topfeed.fun','seuprimeiroempregoam.com']
def die(msg):raise RuntimeError(msg)
def expected(current):
 source=json.loads(SOURCE.read_text());cs=source['campaigns']
 assert source['complete'] and len(cs)==source['campaign_count']==428 and len({c['id'] for c in cs})==len(cs)
 out=copy.deepcopy(current);route_map={(r['host'],r['path']):r for r in out['routes']};catalog={d['id']:d for d in out.get('catalog',[])};groups=set(out.get('groups',[]));seen=set();added=0;issues=[]
 for c in sorted(cs,key=lambda c:c['id']):
  host=urlsplit(c['domain']).hostname
  assert any(host==a or host.endswith('.'+a) for a in APEX)
  reasons=[]
  if c['state']!='active':reasons.append('campaign_not_active')
  if c['type']!='position':reasons.append('campaign_not_position')
  if not re.fullmatch(r'[A-Za-z0-9_-]+',c['alias']):reasons.append('unsupported_alias')
  if len(c['streams'])!=1:reasons.append('multiple_or_zero_streams')
  targets=[];group=c['name'].split(' - ')[0].strip();group=group if group else host
  for s in c['streams']:
   if s['state']!='active' or s['schema']!='landings' or s['type']!='regular':reasons.append('unsupported_stream_state_schema_type')
   if s['filters'] or s['offers'] or s.get('triggers'):reasons.append('filters_offers_or_triggers')
   total=sum(l['share'] for l in s['landings'])
   if not total:reasons.append('zero_total_weight')
   for l in s['landings']:
    if l['state']!='active' or l['action_type']!='http' or l['landing_type']!='external':reasons.append('unsupported_landing_state_type')
    weight=Fraction(l['share']*100,total) if total else 0
    if not weight or weight.denominator!=1 or not 0<weight<=100:reasons.append('percentage_not_positive_integer')
    u=urlsplit(l.get('destination') or '')
    if u.scheme!='https' or u.username or u.fragment:reasons.append('unsupported_destination_URL')
    targets.append({'url':l.get('destination'),'weight':int(weight),'destination_id':'ktr-'+str(l['id'])})
  if reasons:
   issues.append({'id':c['id'],'name':c['name'],'host':host,'reasons':sorted(set(reasons))});continue
  key=(host,'/'+c['alias'])
  if key in seen:die('duplicate_source_route')
  seen.add(key)
  groups.add(group)
  r={'host':host,'path':key[1],'name':c['name'],'group':group}
  if len(targets)==1:r.update(destination=targets[0]['url'],destination_id=targets[0]['destination_id'])
  else:r['destinations']=targets
  for l in c['streams'][0]['landings']:
   id='ktr-'+str(l['id']);d={'id':id,'name':l['name'],'url':l['destination'],'group':group}
   if id in catalog:
    if catalog[id]['name']!=d['name'] or catalog[id]['url']!=d['url']:die('catalog_identity_conflict:'+id)
    # Existing operator group assignments remain untouched.
   else:catalog[id]=d
  if key in route_map:
   if route_map[key]!=r:die('existing_route_conflict:'+host+key[1])
  else:out['routes'].append(r);route_map[key]=r;added+=1
 if issues:return None,{'status':'source_fidelity_blocked','issues':issues,'campaign_count':len(cs),'DNS_writes':0,'route_writes':0}
 out['catalog']=sorted(catalog.values(),key=lambda d:d['id']);out['groups']=sorted(groups)
 return out,{'status':'plan_ready','campaigns':len(cs),'routes_added':added,'new_total_routes':len(out['routes']),'catalog_destinations':len(out['catalog']),'hosts':sorted({urlsplit(c['domain']).hostname for c in cs}),'relative_weights_normalized_exactly':True,'source_raw_weights_preserved_in_snapshot':True}
def item(title):
 p=subprocess.run([str(BASE/'scripts/mgs-op-with-service-account.sh'),'item','get',title,'--vault','MGS Conteúdo','--format','json','--reveal'],capture_output=True,text=True,timeout=45)
 if p.returncode:die('canonical_login_unavailable')
 return json.loads(p.stdout)
def login():
 f={f['id']:f.get('value') for f in item('MGS Router - Rodolfo')['fields']};s=requests.Session()
 r=s.post(PANEL+'/login',data={'username':f['username'],'password':f['password']},headers={'Origin':PANEL},allow_redirects=False,timeout=30)
 if r.status_code!=303 or r.headers.get('Location')!='/admin':die('panel_login_failed')
 r=s.get(PANEL+'/api/me',timeout=30);r.raise_for_status();return s,{'Origin':PANEL,'X-CSRF-Token':r.json()['csrf']}
def read(s,path):
 r=s.get(PANEL+path,timeout=30);r.raise_for_status();return r.json()
def write(s,h,path,payload,wanted):
 try:r=s.post(PANEL+path,json=payload,headers=h,timeout=45)
 except requests.RequestException:
  if read(s,path)!=wanted:die('ambiguous_write_not_proven_complete:'+path)
 else:
  if r.status_code!=200:die('API_write_rejected:'+path+':'+str(r.status_code))
 after=read(s,path)
 if after!=wanted:die('exact_API_readback_mismatch:'+path)
 return after
def main():
 p=argparse.ArgumentParser();p.add_argument('--apply',action='store_true');p.add_argument('--approval-message-id');a=p.parse_args()
 current=json.loads(Path('/var/lib/mgs-router/routes.json').read_text());plan,summary=expected(current)
 if plan is None:
  PLAN.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n');print(json.dumps(summary,ensure_ascii=False));return
 PLAN.write_text(json.dumps({'summary':summary,'configuration':plan},ensure_ascii=False,indent=2)+'\n')
 if not a.apply:print(json.dumps(summary,ensure_ascii=False));return
 if a.approval_message_id!=APPROVAL:die('exact_authorization_required')
 BACKUP.mkdir(mode=0o700,parents=True,exist_ok=True)
 for file in ['routes.json','domains.json','users.json']:
  dest=BACKUP/file
  if dest.exists():die('backup_exists_reconcile_before_replay')
  shutil.copy2(Path('/var/lib/mgs-router')/file,dest);os.chmod(dest,0o600)
 shutil.copy2('/opt/mgs-router/mgs-router',BACKUP/'mgs-router')
 check=subprocess.run([str(BACKUP/'mgs-router'),'--state',str(BACKUP),'--origin',PANEL,'--check'],capture_output=True,text=True,timeout=30)
 if check.returncode:die('backup_binary_state_validation_failed')
 s,h=login();writes=0
 try:
  before=read(s,'/api/routes');plan,summary=expected(before)
  if plan is None:die('source_no_longer_compatible')
  assert plan is not None
  if before!=current:die('concurrent_route_change_before_apply')
  # Exercise the real binary against isolated copied state with the proposed data.
  probe=BACKUP/'candidate-check';probe.mkdir(mode=0o700)
  (probe/'routes.json').write_text(json.dumps(plan));shutil.copy2(BACKUP/'users.json',probe/'users.json');shutil.copy2(BACKUP/'domains.json',probe/'domains.json')
  chk=subprocess.run([str(BACKUP/'mgs-router'),'--state',str(probe),'--origin',PANEL,'--check'],capture_output=True,text=True,timeout=30)
  if chk.returncode:die('proposed_configuration_real_binary_rejected')
  wanted=copy.deepcopy(plan);wanted['revision']=before['revision']+1
  after=write(s,h,'/api/routes',plan,wanted);writes+=1
  domains=read(s,'/api/domains');hosts=summary['hosts'];payload={'revision':domains['revision'],'domains':sorted(set(domains['domains'])|set(hosts))}
  if payload['domains']!=domains['domains']:
   desired={'revision':domains['revision']+1,'domains':payload['domains']}
   # GET may include additional instruction fields; require the exact public revision/domains pair.
   try:r=s.post(PANEL+'/api/domains',json=payload,headers=h,timeout=45)
   except requests.RequestException:r=None
   dom_after=read(s,'/api/domains')
   if dom_after['revision']!=desired['revision'] or dom_after['domains']!=desired['domains']:die('domain_API_readback_mismatch')
   if r is not None and r.status_code!=200:die('domain_write_rejected')
   writes+=1
  assert all(r in after['routes'] for r in before['routes'])
  assert all(d in after['catalog'] for d in before['catalog'])
  report={**summary,'status':'routes_domains_imported_exact_readback','authorization_message_id':APPROVAL,'revision':after['revision'],'API_writes':writes,'DNS_writes':0,'Keitaro_writes':0,'existing_routes_catalog_groups_preserved':True,'backup_binary_state_check_passed':True,'proposed_configuration_real_binary_check_passed':True,'secrets_emitted':False,'validated_at':datetime.now(timezone.utc).isoformat()}
  RESULT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
  with (BASE/'logs/events-audit.jsonl').open('a') as f:f.write(json.dumps({'timestamp':report['validated_at'],'agent':'zeus','action':'mgs_router_eleven_domains_import_validated','thread_id':'1555381168894115912',**report})+'\n')
  print(json.dumps(report,ensure_ascii=False))
 finally:
  r=s.post(PANEL+'/logout',json={},headers=h,timeout=30)
  if r.status_code!=200:die('panel_logout_failed')
if __name__=='__main__':
 try:main()
 except Exception as e:
  print(json.dumps({'status':'failed','error':str(e) if isinstance(e,RuntimeError) else type(e).__name__,'secrets_emitted':False}));sys.exit(1)
