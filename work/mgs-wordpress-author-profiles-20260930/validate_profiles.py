#!/usr/bin/env python3
"""Independent readback of the 57-site MGS author profile rollout."""
from __future__ import annotations
import importlib.util,json,os,tempfile
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path('/root/mgs-agent/work/mgs-wordpress-author-profiles-20260930');ADMIN=ROOT/'admin-preflight.json';STATE=ROOT/'execution-state.json';OUT=ROOT/'validation-summary.json';WPCLI_DOMAINS={'financiamentoautoadx.com','financiarveiculo.com','vizioid.com','xyvlov.com'}

def loadmod(name,path):
 spec=importlib.util.spec_from_file_location(name,path)
 if spec is None or spec.loader is None: raise RuntimeError(f'cannot load module: {path}')
 m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
rest=loadmod('author_rest',ROOT/'apply_admin_rest_profiles.py');wpmod=loadmod('author_wpcli',ROOT/'apply_wpcli_fallback.py')

def validate_profile(domain,label,current,before):
 desired=rest.DESIRED[label];checks={'id':current.get('id')==before.get('id'),'username':current.get('username')==before.get('username'),'slug':current.get('slug')==before.get('slug'),'roles':current.get('roles')==before.get('roles'),'email':current.get('email')==before.get('email'),'name':current.get('name')==desired['name'],'description':current.get('description')==desired['description']}
 return checks

def main():
 mapping={x['domain']:x for x in json.loads(ADMIN.read_text())['results']};state=json.loads(STATE.read_text());results={};failures={}
 for domain,m in sorted(mapping.items()):
  if domain in WPCLI_DOMAINS:continue
  try:
   f=rest.item_fields(m['item_id']);user=f.get(m['username_field'].casefold());pw=f.get(m['password_field'].casefold());
   if not user or not pw:raise RuntimeError('credential fields empty')
   import urllib.parse
   q=urllib.parse.urlencode({'context':'edit','per_page':100,'_fields':'id,username,slug,name,description,roles,email,link'});http,users=rest.req(domain,'/wp-json/wp/v2/users?'+q,user,pw)
   if http!=200 or not isinstance(users,list):raise RuntimeError(f'users HTTP {http}')
   ats=[u for u in users if str(u.get('username') or u.get('slug') or '').casefold()=='atena' or str(u.get('email') or '').casefold()=='atena@matteiservicesinc.com'];rqs=[u for u in users if 'raquel' in ' '.join(str(u.get(k,'') or '') for k in ('username','slug','name','email')).casefold()]
   if len(ats)!=1 or len(rqs)!=1:raise RuntimeError(f'identity counts {len(ats)}/{len(rqs)}')
   sr=state['results'].get(domain,{}).get('profiles',{});checks={'atena':validate_profile(domain,'atena',rest.safe_user(ats[0]),sr['atena']['before']),'raquel':validate_profile(domain,'raquel',rest.safe_user(rqs[0]),sr['raquel']['before'])}
   if not all(all(x.values()) for x in checks.values()):raise RuntimeError('readback mismatch')
   results[domain]={'route':'admin_rest','profiles':{'atena':rest.safe_user(ats[0]),'raquel':rest.safe_user(rqs[0])},'checks':checks}
  except Exception as e:failures[domain]={'route':'admin_rest','error':type(e).__name__+': '+str(e)[:400]}
 # independent WP-CLI readback for four sites
 rows={x['domain']:x for x in json.loads(wpmod.MANIFEST.read_text())['targets'] if x['domain'] in WPCLI_DOMAINS}
 for domain,row in sorted(rows.items()):
  pwpath=None
  try:
   pw=wpmod.server_password(row['host'])
   with tempfile.NamedTemporaryFile(mode='w',prefix='mgs-author-validate-ssh-',delete=False) as fh:pwpath=Path(fh.name);fh.write(pw);fh.flush();os.fchmod(fh.fileno(),0o600)
   remote='''set -euo pipefail
path="$1"; owner="$2"
wpcli() { runuser -u "$owner" -- wp --path="$path" "$@" --skip-plugins --skip-themes; }
profile() { login="$1"; uid=$(wpcli user get "$login" --field=ID); data=$(wpcli user get "$uid" --fields=ID,user_login,user_nicename,user_email,display_name,roles --format=json); desc=$(wpcli user meta get "$uid" description 2>/dev/null || true); python3 - "$data" "$desc" <<'PY'
import json,sys
d=json.loads(sys.argv[1]);print(json.dumps({'id':int(d['ID']),'username':d['user_login'],'slug':d['user_nicename'],'name':d['display_name'],'description':sys.argv[2],'roles':d['roles'],'email':d['user_email']},separators=(',',':')))
PY
}
a=$(profile atena); r=$(profile raqueloliveira); python3 - "$a" "$r" <<'PY'
import json,sys;print(json.dumps({'atena':json.loads(sys.argv[1]),'raquel':json.loads(sys.argv[2])},separators=(',',':')))
PY
'''
   proc=wpmod.run(['sshpass','-f',str(pwpath),'ssh','-o','PreferredAuthentications=password','-o','PubkeyAuthentication=no','-o','StrictHostKeyChecking=accept-new','-o','UserKnownHostsFile=/root/.ssh/known_hosts_mgs',f"zeus@{row['host']}",'sudo','-n','bash','-s','--',row['path'],row['owner']],input_bytes=remote.encode(),timeout=240);profiles=json.loads(proc.stdout.decode().strip().splitlines()[-1]);sr=state['results'][domain]['profiles'];checks={'atena':validate_profile(domain,'atena',profiles['atena'],sr['atena']['before']),'raquel':validate_profile(domain,'raquel',profiles['raquel'],sr['raquel']['before'])}
   if not all(all(x.values()) for x in checks.values()):raise RuntimeError('readback mismatch')
   results[domain]={'route':'runcloud_wpcli','profiles':profiles,'checks':checks}
  except Exception as e:failures[domain]={'route':'runcloud_wpcli','error':type(e).__name__+': '+str(e)[:400]}
  finally:
   try:
    if pwpath is not None: pwpath.unlink(missing_ok=True)
   except:pass
 expected=57;payload={'operation':'mgs-wordpress-author-profiles-20260930','validated_at':datetime.now(timezone.utc).isoformat(),'expected_sites':expected,'validated_sites':len(results),'validated_profiles':len(results)*2,'routes':{'admin_rest':sum(x['route']=='admin_rest' for x in results.values()),'runcloud_wpcli':sum(x['route']=='runcloud_wpcli' for x in results.values())},'failures':failures,'status':'PASS' if len(results)==expected and not failures else 'FAIL','secret_values_recorded':False,'results':results};OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n');OUT.chmod(0o600);print(json.dumps({k:payload[k] for k in ('status','expected_sites','validated_sites','validated_profiles','routes','failures','secret_values_recorded')},ensure_ascii=False,indent=2));return 0 if payload['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
