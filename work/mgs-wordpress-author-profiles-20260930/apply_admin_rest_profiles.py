#!/usr/bin/env python3
"""Apply and read back generic MGS author profiles via admin REST."""
from __future__ import annotations
import argparse,base64,json,subprocess,time,urllib.error,urllib.parse,urllib.request
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path('/root/mgs-agent/work/mgs-wordpress-author-profiles-20260930');PREFLIGHT=ROOT/'admin-preflight.json';STATE=ROOT/'execution-state.json';VAULT='MGS Conteúdo'
ATENA_BIO='Atena is a creative writer at MGS Digital Corp, focused on producing clear, engaging, and well-researched content for readers across different topics and markets.'
RAQUEL_BIO='Raquel Oliveira is a writer and content editor at MGS Digital Corp, focused on editorial quality, clear communication, and useful content for readers across different topics and markets.'
DESIRED={'atena':{'name':'Atena','description':ATENA_BIO},'raquel':{'name':'Raquel Oliveira','description':RAQUEL_BIO}}

def run(args,attempts=3):
 last=''
 for n in range(1,attempts+1):
  p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
  if p.returncode==0:return p.stdout
  last=p.stderr.decode('utf-8','replace')[:500]
  if n<attempts:time.sleep(2*n)
 raise RuntimeError(last)

def item_fields(item_id):
 raw=json.loads(run(['op','item','get',item_id,'--vault',VAULT,'--format','json','--reveal']));out={}
 for f in raw.get('fields',[]):
  for k in (f.get('id'),f.get('label')):
   if k:out[str(k).casefold()]=f.get('value','')
 return out

def req(domain,path,user,pw,method='GET',payload=None):
 token=base64.b64encode(f'{user}:{pw}'.encode()).decode();headers={'Authorization':'Basic '+token,'Accept':'application/json','User-Agent':'MGS-Atena-Author-Profile/1.0'};data=None
 if payload is not None:data=json.dumps(payload).encode();headers['Content-Type']='application/json'
 r=urllib.request.Request('https://'+domain+path,headers=headers,data=data,method=method)
 try:
  with urllib.request.urlopen(r,timeout=60) as x:raw=x.read();return x.status,json.loads(raw) if raw else None
 except urllib.error.HTTPError as e:
  raw=e.read()
  try:b=json.loads(raw) if raw else None
  except:b={'non_json':raw[:200].decode('utf-8','replace')}
  return e.code,b

def safe_user(u):return {k:u.get(k) for k in ('id','username','slug','name','description','roles','email','link')}
def load_state():
 if STATE.exists():return json.loads(STATE.read_text())
 return {'operation':'mgs-wordpress-author-profiles-20260930','authorization_message_id':'1554987073994489907','started_at':datetime.now(timezone.utc).isoformat(),'results':{},'failures':{},'secret_values_recorded':False}
def save(s):
 s['updated_at']=datetime.now(timezone.utc).isoformat();tmp=STATE.with_suffix('.tmp');tmp.write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n');tmp.chmod(0o600);tmp.replace(STATE)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('domains',nargs='*');args=ap.parse_args();pf=json.loads(PREFLIGHT.read_text());mapping={x['domain']:x for x in pf['results']};targets=args.domains or sorted(mapping);state=load_state()
 for domain in targets:
  if domain not in mapping:state['failures'][domain]={'stage':'mapping','error':'no admin REST mapping'};save(state);continue
  try:
   m=mapping[domain];f=item_fields(m['item_id']);user=f.get(m['username_field'].casefold());pw=f.get(m['password_field'].casefold())
   if not user or not pw:raise RuntimeError('credential fields empty')
   q=urllib.parse.urlencode({'context':'edit','per_page':100,'_fields':'id,username,slug,name,description,roles,email,link'});http,users=req(domain,'/wp-json/wp/v2/users?'+q,user,pw)
   if http!=200 or not isinstance(users,list):raise RuntimeError(f'users pre-read HTTP {http}')
   exact={
    'atena':[u for u in users if str(u.get('username') or u.get('slug') or '').casefold()=='atena' or str(u.get('email') or '').casefold()=='atena@matteiservicesinc.com'],
    'raquel':[u for u in users if 'raquel' in ' '.join(str(u.get(k,'') or '') for k in ('username','slug','name','email')).casefold()],
   }
   if len(exact['atena'])!=1 or len(exact['raquel'])!=1:raise RuntimeError(f"identity counts atena={len(exact['atena'])} raquel={len(exact['raquel'])}")
   domain_result={'domain':domain,'route':'admin_rest','profiles':state.get('results',{}).get(domain,{}).get('profiles',{})}
   for label in ('atena','raquel'):
    before=safe_user(exact[label][0]);desired=DESIRED[label];uid=int(before['id'])
    if before.get('name')==desired['name'] and before.get('description')==desired['description']:
     action='unchanged'
    else:
     wh,wb=req(domain,f'/wp-json/wp/v2/users/{uid}',user,pw,method='POST',payload={'name':desired['name'],'description':desired['description']})
     if wh!=200:raise RuntimeError(f'{label} update HTTP {wh} code={wb.get("code") if isinstance(wb,dict) else None}')
     action='updated'
    rh,after=req(domain,f'/wp-json/wp/v2/users/{uid}?context=edit&_fields=id,username,slug,name,description,roles,email,link',user,pw)
    if rh!=200 or not isinstance(after,dict):raise RuntimeError(f'{label} readback HTTP {rh}')
    checks={'id':after.get('id')==before.get('id'),'username':after.get('username')==before.get('username'),'slug':after.get('slug')==before.get('slug'),'roles':after.get('roles')==before.get('roles'),'email':after.get('email')==before.get('email'),'name':after.get('name')==desired['name'],'description':after.get('description')==desired['description']}
    if not all(checks.values()):raise RuntimeError(f'{label} readback mismatch {[k for k,v in checks.items() if not v]}')
    domain_result['profiles'][label]={'action':action,'before':before,'after':safe_user(after),'checks':checks,'http':{'readback':rh}}
    state['results'][domain]=domain_result;state['failures'].pop(domain,None);save(state)
   state['results'][domain]=domain_result;state['failures'].pop(domain,None);save(state);print(f'PASS {domain} atena={domain_result["profiles"]["atena"]["action"]} raquel={domain_result["profiles"]["raquel"]["action"]}')
  except Exception as e:
   state['failures'][domain]={'stage':'apply_admin_rest','error':type(e).__name__+': '+str(e)[:500],'at':datetime.now(timezone.utc).isoformat()};save(state);print(f'FAIL {domain} {type(e).__name__}: {str(e)[:300]}')
 summary={'requested':len(targets),'completed':sum(1 for d in targets if d in state['results'] and all(x in state['results'][d].get('profiles',{}) for x in ('atena','raquel'))),'failures':{d:state['failures'][d] for d in targets if d in state['failures']},'writes':sum(1 for d in targets for p in state.get('results',{}).get(d,{}).get('profiles',{}).values() if p.get('action')=='updated')}
 print(json.dumps(summary,ensure_ascii=False,indent=2));return 0 if summary['completed']==len(targets) and not summary['failures'] else 1
if __name__=='__main__':raise SystemExit(main())
