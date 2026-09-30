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
  ab64=base64.b64encode(ATENA_BIO.encode()).decode();rb64=base64.b64encode(RAQUEL_BIO.encode()).decode();php=f'''$out=[]; $targets=[['label'=>'atena','login'=>'atena','name'=>'Atena','bio'=>base64_decode('{ab64}')],['label'=>'raquel','login'=>'raqueloliveira','name'=>'Raquel Oliveira','bio'=>base64_decode('{rb64}')]]; foreach($targets as $t){{ $u=get_user_by('login',$t['login']); if(!$u){{ fwrite(STDERR,'missing_'.$t['label']); exit(20); }} $before=['id'=>(int)$u->ID,'username'=>$u->user_login,'slug'=>$u->user_nicename,'name'=>$u->display_name,'description'=>get_user_meta($u->ID,'description',true),'roles'=>array_values($u->roles),'email'=>$u->user_email]; $action=($before['name']===$t['name'] && $before['description']===$t['bio'])?'unchanged':'updated'; if($action==='updated'){{ $r=wp_update_user(['ID'=>$u->ID,'display_name'=>$t['name'],'description'=>$t['bio']]); if(is_wp_error($r)){{ fwrite(STDERR,$r->get_error_code()); exit(21); }} }} clean_user_cache($u->ID); $a=get_userdata($u->ID); $after=['id'=>(int)$a->ID,'username'=>$a->user_login,'slug'=>$a->user_nicename,'name'=>$a->display_name,'description'=>get_user_meta($a->ID,'description',true),'roles'=>array_values($a->roles),'email'=>$a->user_email]; $checks=['id'=>$after['id']===$before['id'],'username'=>$after['username']===$before['username'],'slug'=>$after['slug']===$before['slug'],'roles'=>$after['roles']===$before['roles'],'email'=>$after['email']===$before['email'],'name'=>$after['name']===$t['name'],'description'=>$after['description']===$t['bio']]; if(in_array(false,$checks,true)){{ fwrite(STDERR,'readback_'.$t['label']); exit(22); }} $out[$t['label']]=['action'=>$action,'before'=>$before,'after'=>$after,'checks'=>$checks]; }} echo json_encode($out,JSON_UNESCAPED_SLASHES|JSON_UNESCAPED_UNICODE);'''
  try:
   proc=run(['sshpass','-f',str(pwpath),'ssh','-o','PreferredAuthentications=password','-o','PubkeyAuthentication=no','-o','StrictHostKeyChecking=accept-new','-o','UserKnownHostsFile=/root/.ssh/known_hosts_mgs',f'zeus@{host}','sudo','-n','-u',row['owner'],'wp',f'--path={row["path"]}','eval',php,'--skip-plugins','--skip-themes'],timeout=240)
   profiles=json.loads(proc.stdout.decode());state['results'][domain]={'domain':domain,'route':'runcloud_wpcli','host':host,'path':row['path'],'profiles':profiles};state['failures'].pop(domain,None);save(state);print(f'PASS {domain} atena={profiles["atena"]["action"]} raquel={profiles["raquel"]["action"]}')
  except Exception as e:
   state['failures'][domain]={'stage':'apply_wpcli','error':type(e).__name__+': '+str(e)[:500],'at':datetime.now(timezone.utc).isoformat()};save(state);fail[domain]=state['failures'][domain];print(f'FAIL {domain} {type(e).__name__}: {str(e)[:300]}')
  finally:pwpath.unlink(missing_ok=True)
 print(json.dumps({'requested':len(TARGETS),'completed':sum(d in state['results'] for d in TARGETS),'failures':fail},ensure_ascii=False,indent=2));return 0 if not fail and all(d in state['results'] for d in TARGETS) else 1
if __name__=='__main__':raise SystemExit(main())
