#!/usr/bin/env python3
"""Resolve an admin-capable REST route for allowlisted MGS sites (read-only)."""
from __future__ import annotations
import base64,json,subprocess,time,urllib.error,urllib.parse,urllib.request
from pathlib import Path

ROOT=Path('/root/mgs-agent/work/mgs-wordpress-author-profiles-20260930');OUT=ROOT/'admin-preflight.json';VAULT='MGS Conteúdo'

def run(args,attempts=3):
 last=''
 for n in range(1,attempts+1):
  p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
  if p.returncode==0:return p.stdout
  last=p.stderr.decode('utf-8','replace')[:500]
  if n<attempts:time.sleep(2*n)
 raise RuntimeError(last)

def req(domain,path,user,pw,method='GET',payload=None):
 token=base64.b64encode(f'{user}:{pw}'.encode()).decode();headers={'Authorization':'Basic '+token,'Accept':'application/json','User-Agent':'MGS-Atena-Admin-Preflight/1.0'};data=None
 if payload is not None:data=json.dumps(payload).encode();headers['Content-Type']='application/json'
 r=urllib.request.Request('https://'+domain+path,headers=headers,data=data,method=method)
 try:
  with urllib.request.urlopen(r,timeout=45) as x:raw=x.read();return x.status,json.loads(raw) if raw else None
 except urllib.error.HTTPError as e:
  raw=e.read()
  try:b=json.loads(raw) if raw else None
  except:b={'non_json':raw[:120].decode('utf-8','replace')}
  return e.code,b

def field_map(raw):
 out={}
 for f in raw.get('fields',[]):
  for k in (f.get('id'),f.get('label')):
   if k:out[str(k).casefold()]=f.get('value','')
 return out

def extract(f):
 user=next((f.get(k) for k in ['api_auth_user','app user','username'] if f.get(k)),None)
 pw=next((f.get(k) for k in ['api_application_password','wp_app_password','app password'] if f.get(k)),None)
 return user,pw

def rank(title):
 t=title.casefold()
 if t.startswith('zeus wordpress - '):return 0
 if 'rmmaster' in t:return 3
 if t.startswith('wordpress - ') or t.startswith('wordpress -'):return 1
 if t.startswith('wordpress '):return 1
 return 2

def main():
 allowed=[x.strip() for x in subprocess.check_output(['python3','/root/mgs-agent/scripts/mgs-domain-scope.py','list','--agent','atena'],text=True).splitlines() if x.strip()]
 items=json.loads(run(['op','item','list','--vault',VAULT,'--format','json']))
 results=[];fail=[]
 for domain in allowed:
  cand=[]
  for x in items:
   title=x.get('title','')
   if title.startswith('Atena WordPress - '):continue
   hosts={urllib.parse.urlparse(u.get('href','')).hostname for u in x.get('urls') or []}
   if domain in hosts and 'wordpress' in title.casefold():cand.append(x)
  cand.sort(key=lambda x:(rank(x.get('title','')),x.get('title','')))
  selected=None;attempts=[]
  for x in cand:
   try:
    raw=json.loads(run(['op','item','get',x['id'],'--vault',VAULT,'--format','json','--reveal']))
    fm=field_map(raw);user,pw=extract(fm)
    if not user or not pw:
     attempts.append({'title':x.get('title'),'result':'missing_api_fields'});continue
    q=urllib.parse.urlencode({'context':'edit','per_page':100,'_fields':'id,username,slug,name,description,roles,email,link'})
    http,body=req(domain,'/wp-json/wp/v2/users?'+q,user,pw)
    if http!=200 or not isinstance(body,list):
     code=body.get('code') if isinstance(body,dict) else None;attempts.append({'title':x.get('title'),'result':f'http_{http}','code':code});continue
    at=[u for u in body if str(u.get('username') or u.get('slug') or '').casefold()=='atena' or str(u.get('email') or '').casefold()=='atena@matteiservicesinc.com']
    rq=[u for u in body if 'raquel' in ' '.join(str(u.get(k,'') or '') for k in ('username','slug','name','email')).casefold()]
    if len(at)!=1 or len(rq)!=1:
     attempts.append({'title':x.get('title'),'result':'identity_count','atena':len(at),'raquel':len(rq)});continue
    selected={'domain':domain,'route':'admin_rest','item_id':x['id'],'item_title':x.get('title'),'username_field':next(k for k in ['api_auth_user','app user','username'] if fm.get(k)==user),'password_field':next(k for k in ['api_application_password','wp_app_password','app password'] if fm.get(k)==pw),'atena':{k:at[0].get(k) for k in ('id','username','slug','name','description','roles','email','link')},'raquel':{k:rq[0].get(k) for k in ('id','username','slug','name','description','roles','email','link')}}
    break
   except Exception as e:attempts.append({'title':x.get('title'),'result':type(e).__name__+': '+str(e)[:120]})
  if selected:results.append(selected)
  else:fail.append({'domain':domain,'candidates':len(cand),'attempts':attempts})
  OUT.write_text(json.dumps({'status':'in_progress','results':results,'failures':fail,'secret_values_recorded':False},ensure_ascii=False,indent=2)+'\n');time.sleep(.15)
 payload={'status':'PASS' if len(results)==len(allowed) else 'PARTIAL','expected':len(allowed),'admin_rest_ready':len(results),'fallback_required':len(fail),'results':results,'failures':fail,'secret_values_recorded':False}
 OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'status':payload['status'],'expected':payload['expected'],'admin_rest_ready':payload['admin_rest_ready'],'fallback_required':payload['fallback_required'],'fallback_domains':[x['domain'] for x in fail]},ensure_ascii=False,indent=2));return 0 if payload['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
