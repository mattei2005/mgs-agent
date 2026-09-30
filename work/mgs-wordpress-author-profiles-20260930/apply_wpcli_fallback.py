#!/usr/bin/env python3
"""Apply author profile standard to the four RunCloud fallback sites via WP-CLI."""
from __future__ import annotations
import base64,json,os,subprocess,tempfile,time
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path('/root/mgs-agent/work/mgs-wordpress-author-profiles-20260930');STATE=ROOT/'execution-state.json';MANIFEST=Path('/root/mgs-agent/work/atena-wordpress-access-20260920/runcloud-preflight.json');VAULT='MGS Conteúdo'
TARGETS={'financiamentoautoadx.com','financiarveiculo.com','vizioid.com','xyvlov.com'}
SERVER_ITEMS={'162.55.28.179':'Runcloud Server 02 - 162.55.28.179- zeus Acesso','46.4.95.117':'Runcloud Server 03 - 46.4.95.117- zeus Acesso'}
ATENA_BIO='Atena is a creative writer at MGS Digital Corp, focused on producing clear, engaging, and well-researched content for readers across different topics and markets.'
RAQUEL_BIO='Raquel Oliveira is a writer and content editor at MGS Digital Corp, focused on editorial quality, clear communication, and useful content for readers across different topics and markets.'

def run(args,input_bytes=None,timeout=240,check=True):
 p=subprocess.run(args,input=input_bytes,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout)
 if check and p.returncode:raise RuntimeError(f'rc={p.returncode} stderr={p.stderr.decode("utf-8","replace")[:500]}')
 return p

def op(args):return run(['op',*args],timeout=180).stdout

def server_password(host):
 items=json.loads(op(['item','list','--vault',VAULT,'--format','json']));title=SERVER_ITEMS[host];item=next(x for x in items if x.get('title','').casefold()==title.casefold());value=op(['item','get',item['id'],'--vault',VAULT,'--fields','label=password','--reveal']).decode().strip();
 if not value:raise RuntimeError('empty server password')
 return value

def load_state():return json.loads(STATE.read_text())
def save(s):
 s['updated_at']=datetime.now(timezone.utc).isoformat();tmp=STATE.with_suffix('.tmp');tmp.write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n');tmp.chmod(0o600);tmp.replace(STATE)

def main():
 rows={x['domain']:x for x in json.loads(MANIFEST.read_text())['targets'] if x['domain'] in TARGETS};assert set(rows)==TARGETS
 state=load_state();fail={}
 for domain in sorted(TARGETS):
  row=rows[domain];host=row['host'];pw=server_password(host)
  with tempfile.NamedTemporaryFile(mode='w',prefix='mgs-author-ssh-',delete=False) as fh:pwpath=Path(fh.name);fh.write(pw);fh.flush();os.fchmod(fh.fileno(),0o600)
  ab64=base64.b64encode(ATENA_BIO.encode()).decode();rb64=base64.b64encode(RAQUEL_BIO.encode()).decode()
  remote=f'''set -euo pipefail
path="$1"
owner="$2"
atena_bio=$(printf '%s' '{ab64}' | base64 -d)
raquel_bio=$(printf '%s' '{rb64}' | base64 -d)
wpcli() {{ runuser -u "$owner" -- wp --path="$path" "$@" --skip-plugins --skip-themes; }}
profile() {{
  login="$1"
  uid=$(wpcli user get "$login" --field=ID)
  data=$(wpcli user get "$uid" --fields=ID,user_login,user_nicename,user_email,display_name,roles --format=json)
  desc=$(wpcli user meta get "$uid" description 2>/dev/null || true)
  python3 - "$data" "$desc" <<'PY'
import json,sys
d=json.loads(sys.argv[1]);print(json.dumps({{'id':int(d['ID']),'username':d['user_login'],'slug':d['user_nicename'],'name':d['display_name'],'description':sys.argv[2],'roles':d['roles'],'email':d['user_email']}},separators=(',',':')))
PY
}}
before_atena=$(profile atena)
before_raquel=$(profile raqueloliveira)
action_atena=unchanged
action_raquel=unchanged
if [ "$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["name"])' "$before_atena")" != "Atena" ] || [ "$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["description"])' "$before_atena")" != "$atena_bio" ]; then
  wpcli user update atena --display_name='Atena' --description="$atena_bio" >/dev/null
  action_atena=updated
fi
if [ "$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["name"])' "$before_raquel")" != "Raquel Oliveira" ] || [ "$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["description"])' "$before_raquel")" != "$raquel_bio" ]; then
  wpcli user update raqueloliveira --display_name='Raquel Oliveira' --description="$raquel_bio" >/dev/null
  action_raquel=updated
fi
after_atena=$(profile atena)
after_raquel=$(profile raqueloliveira)
python3 - "$before_atena" "$after_atena" "$action_atena" "$before_raquel" "$after_raquel" "$action_raquel" <<'PY'
import json,sys
ba,aa,aca,br,ar,acr=sys.argv[1:]
ba,aa,br,ar=map(json.loads,(ba,aa,br,ar))
def row(label,before,after,action,name,bio):
 checks={{'id':after['id']==before['id'],'username':after['username']==before['username'],'slug':after['slug']==before['slug'],'roles':after['roles']==before['roles'],'email':after['email']==before['email'],'name':after['name']==name,'description':after['description']==bio}}
 if not all(checks.values()): raise SystemExit('readback_'+label+'_'+','.join(k for k,v in checks.items() if not v))
 return {{'action':action,'before':before,'after':after,'checks':checks}}
print(json.dumps({{'atena':row('atena',ba,aa,aca,'Atena','{ATENA_BIO}'),'raquel':row('raquel',br,ar,acr,'Raquel Oliveira','{RAQUEL_BIO}')}},ensure_ascii=False,separators=(',',':')))
PY
'''
  try:
   proc=run(['sshpass','-f',str(pwpath),'ssh','-o','PreferredAuthentications=password','-o','PubkeyAuthentication=no','-o','StrictHostKeyChecking=accept-new','-o','UserKnownHostsFile=/root/.ssh/known_hosts_mgs',f'zeus@{host}','sudo','-n','bash','-s','--',row['path'],row['owner']],input_bytes=remote.encode(),timeout=240)
   profiles=json.loads(proc.stdout.decode().strip().splitlines()[-1]);state['results'][domain]={'domain':domain,'route':'runcloud_wpcli','host':host,'path':row['path'],'profiles':profiles};state['failures'].pop(domain,None);save(state);print(f'PASS {domain} atena={profiles["atena"]["action"]} raquel={profiles["raquel"]["action"]}')
  except Exception as e:
   state['failures'][domain]={'stage':'apply_wpcli','error':type(e).__name__+': '+str(e)[:500],'at':datetime.now(timezone.utc).isoformat()};save(state);fail[domain]=state['failures'][domain];print(f'FAIL {domain} {type(e).__name__}: {str(e)[:300]}')
  finally:pwpath.unlink(missing_ok=True)
 print(json.dumps({'requested':len(TARGETS),'completed':sum(d in state['results'] for d in TARGETS),'failures':fail},ensure_ascii=False,indent=2));return 0 if not fail and all(d in state['results'] for d in TARGETS) else 1
if __name__=='__main__':raise SystemExit(main())
