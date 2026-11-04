#!/usr/bin/env python3
"""Authorized, handoff-gated Hermes cutover. Default is read-only preflight."""
from __future__ import annotations
import argparse,datetime,fcntl,hashlib,importlib.util,json,os,pathlib,re,shutil,sqlite3,stat,subprocess,sys,time,traceback,urllib.request,uuid
M=pathlib.Path('/root/mgs-agent')
R=M/'reports/hermes-updates/20261103-activation-1567354570823172209'
PLAN=R/'execution-plan.json'
STATE=R/'execution-state.json'
THREAD='1567354570823172209'
AUTHORITY='1567390752403755019'
BOT='1496296175014252634'
BACKUP=pathlib.Path('/root/.hermes/secure-backups/hermes-update/20261103-phase4-1567354570823172209')
SCRATCH=pathlib.Path('/root/.hermes/profiles/zeus/cache/scratch/hermes-activate-1567354570823172209')
ORDER=['ares','atena','zeus']

def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(path):
 h=hashlib.sha256()
 with pathlib.Path(path).open('rb') as f:
  while chunk:=f.read(1048576):h.update(chunk)
 return h.hexdigest()
def save(path,data):
 path=pathlib.Path(path);path.parent.mkdir(parents=True,exist_ok=True);p=SCRATCH/('write-'+uuid.uuid4().hex+'.json');p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n');os.chmod(p,0o600);os.replace(p,path)
def audit(event,**data):
 with (M/'logs/events-audit.jsonl').open('a') as out:out.write(json.dumps({'ts':now(),'event':event,'actor':'zeus-hermes-authorized-cutover','authority_message_id':AUTHORITY,'thread_id':THREAD,**data},ensure_ascii=False)+'\n')
def run(cmd,timeout=120,env=None,cwd=None):return subprocess.run(cmd,timeout=timeout,env=env,cwd=cwd,text=True,capture_output=True)
def safe_env(agent=None):
 env={'PATH':os.environ.get('PATH','/usr/local/bin:/usr/bin:/bin'),'HOME':'/root','LANG':'C.UTF-8','TZ':'America/New_York','TMPDIR':str(SCRATCH/'tmp'),'TMP':str(SCRATCH/'tmp'),'TEMP':str(SCRATCH/'tmp')}
 if agent:env['HERMES_HOME']=str(pathlib.Path('/root/.hermes/profiles',agent))
 return env
_token=None
def api(method,path,payload=None):
 global _token
 if _token is None:
  spec=importlib.util.spec_from_file_location('zeus_discord_poster',M/'scripts/discord-bot-post.py');assert spec and spec.loader;module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);module.load_env(module.DEFAULT_ENV);_token=os.environ.get('DISCORD_BOT_TOKEN');assert _token,'bot credential unavailable'
 data=json.dumps(payload,ensure_ascii=False).encode() if payload is not None else None
 req=urllib.request.Request('https://discord.com/api/v10'+path,data=data,method=method,headers={'Authorization':'Bot '+_token,'User-Agent':'MGS-Zeus/1.0','Content-Type':'application/json'})
 with urllib.request.urlopen(req,timeout=25) as response:return json.load(response)
def proc_env(pid):
 values={}
 for row in pathlib.Path('/proc',str(pid),'environ').read_bytes().split(b'\0'):
  if b'=' in row:
   key,value=row.split(b'=',1);values[key.decode()]=value.decode(errors='surrogateescape')
 for key in list(values):
  if key.startswith(('HERMES_SESSION','__HERMES_TEST','HERMES_GATEWAY_SESSION','HERMES_SCRATCH')):values.pop(key,None)
 return values

def svc(agent):
 q=run(['systemctl','show',agent+'-gateway.service','-p','MainPID','-p','ActiveState','-p','SubState','-p','NRestarts','-p','ExecMainStartTimestamp']);assert q.returncode==0
 return dict(line.split('=',1) for line in q.stdout.splitlines() if '=' in line)
def current_state():return json.loads(STATE.read_text()) if STATE.exists() else {'authority':AUTHORITY,'thread_id':THREAD,'status':'prepared','agents':{},'applied_paths':[],'created_at':now()}
def set_state(state,status,**extra):state.update(status=status,updated_at=now(),**extra);save(STATE,state)
def load_plan():
 p=json.loads(PLAN.read_text());assert p['authority']==AUTHORITY and p['thread_id']==THREAD and p['order']==ORDER
 assert sha(p['skills_manifest'])==p['skills_manifest_sha256'];return p

def verify_static(plan):
 assert run(['git','-C',plan['source'],'rev-parse','HEAD']).stdout.strip()==plan['port']
 assert not run(['git','-C',plan['source'],'status','--porcelain=v1']).stdout.strip()
 for path,digest in plan['static_hashes'].items():assert sha(path)==digest,('static drift',path)
 for row in plan['skill_entries']:
  assert sha(row['prepared_source'])==row['after_sha256'],('prepared skill drift',row['path'])
 for archive in plan['recovery_archives']:assert sha(archive['path'])==archive['sha256']
 assert shutil.which('systemd-run'),'No cron fallback is authorized'
 assert sha(plan['installation_stamp'])==plan['installation_stamp_sha256']

def verify_skill_inputs(plan,state):
 applied=set(state.get('applied_paths',[]))
 for row in plan['skill_entries']:
  path=pathlib.Path(row['path']);assert not path.is_symlink(),('skill became symlink',str(path))
  expected=row['after_sha256'] if str(path) in applied else row['before_sha256']
  actual=sha(path) if path.is_file() else None
  assert actual==expected,('unapproved skill drift',str(path))

def preflight(plan):
 verify_static(plan);state=current_state();verify_skill_inputs(plan,state)
 assert pathlib.Path('/root/.local/bin/hermes').resolve()==pathlib.Path(plan['old_launcher'])
 for agent in ORDER:
  service=svc(agent);assert service['ActiveState']=='active' and service['SubState']=='running'
  assert service['MainPID']==plan['old_pids'][agent],('gateway changed since freeze',agent)
  for name,digest in plan['profile_config_hashes'][agent].items():assert sha(pathlib.Path('/root/.hermes/profiles',agent,name))==digest,('profile drift',agent,name)
 return {'preflight':'PASS','source':plan['port'],'skills':len(plan['skill_entries']),'order':ORDER,'live_launcher_unchanged':True,'scheduled':False}

def wait_handoff(plan,state):
 set_state(state,'waiting_for_delivered_handoff');deadline=time.monotonic()+1200
 while time.monotonic()<deadline:
  for msg in api('GET','/channels/'+THREAD+'/messages?limit=50'):
   if int(msg['id'])>int(AUTHORITY) and str(msg.get('author',{}).get('id'))==BOT and msg.get('content')==plan['handoff_text']:
    exact=api('GET','/channels/'+THREAD+'/messages/'+msg['id']);assert exact.get('content')==plan['handoff_text'];set_state(state,'handoff_verified',handoff_message_id=msg['id']);audit('hermes_activation_handoff_verified',message_id=msg['id']);return
  time.sleep(4)
 raise RuntimeError('delivered handoff not observed; no gateway touched')

def atomic_launcher(target):
 dest=pathlib.Path('/root/.local/bin/hermes');temp=SCRATCH/('launcher-'+uuid.uuid4().hex);os.symlink(target,temp);os.replace(temp,dest);assert dest.resolve()==pathlib.Path(target).resolve()

def fresh_profile_backup(agent,state):
 home=pathlib.Path('/root/.hermes/profiles',agent);dest=BACKUP/'cutover-checkpoints'/agent;dest.mkdir(parents=True,exist_ok=False);os.chmod(dest,0o700);entries=[]
 # The service is stopped, so checkpoint/cron DBs and config can be captured without that writer.
 for source in sorted(home.rglob('*.db')):
  rel=source.relative_to(home)
  if len(rel.parts)>1 and rel.parts[0] not in {'cron','state','gateway','platforms','sessions'}:continue
  target=dest/rel;target.parent.mkdir(parents=True,exist_ok=True)
  if source.stat().st_size==0:target.write_bytes(b'');entries.append({'path':str(rel),'kind':'preserved_empty_file','sha256':sha(target)});continue
  a=sqlite3.connect(source.as_uri()+'?mode=ro',uri=True,timeout=15);b=sqlite3.connect(target)
  try:a.backup(b,pages=8192,sleep=.03);b.commit();assert b.execute('PRAGMA integrity_check').fetchall()==[('ok',)]
  finally:b.close();a.close()
  entries.append({'path':str(rel),'kind':'consistent_sqlite','sha256':sha(target),'integrity':'ok'})
 for name in ['config.yaml','SOUL.md','auth.json','.env','honcho.json','discord_threads.json','channel_directory.json']:
  source=home/name
  if source.is_file():shutil.copy2(source,dest/name);entries.append({'path':name,'kind':'control','sha256':sha(dest/name)})
 save(dest/'snapshot-manifest.json',entries);state['agents'].setdefault(agent,{})['fresh_backup']={'path':str(dest),'files':len(entries),'consistent':True};save(STATE,state)

def write_skill(row,state):
 dest=pathlib.Path(row['path']);agent=row['profile'];before=row['before_sha256'];assert (sha(dest) if dest.is_file() else None)==before
 backup=BACKUP/'skills-before-cutover'/agent/row['relative']
 if before is not None:backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(dest,backup);assert sha(backup)==before
 source=pathlib.Path(row['prepared_source']);temp=SCRATCH/('skill-'+uuid.uuid4().hex);temp.write_bytes(source.read_bytes());os.chmod(temp,stat.S_IMODE(dest.stat().st_mode) if dest.is_file() else stat.S_IMODE(source.stat().st_mode));dest.parent.mkdir(parents=True,exist_ok=True);os.replace(temp,dest);assert sha(dest)==row['after_sha256']
 state['applied_paths'].append(str(dest));save(STATE,state)

def apply_skills(agent,plan,state):
 rows=[x for x in plan['skill_entries'] if x['profile']==agent]
 # Native provenance/manifest last; no automatic directory replacement or deletion.
 rows.sort(key=lambda x:(x['relative'].startswith(('.bundled_manifest','.hub/')),x['relative']))
 for row in rows:write_skill(row,state)
 state['agents'].setdefault(agent,{})['skills_applied']=len(rows);save(STATE,state)

def snapshot_paths(agent,plan):
 files=[*plan['static_hashes'],plan['installation_stamp'],str(PLAN),str(pathlib.Path(__file__).resolve()),plan['skills_manifest']]
 files.extend(str(pathlib.Path('/root/.hermes/profiles',agent,name)) for name in ['config.yaml','SOUL.md'])
 files.extend(row['path'] for row in plan['skill_entries'] if row['profile']==agent)
 files.extend(str(p) for p in pathlib.Path('/root/.hermes/profiles',agent,'plugins/honcho').rglob('*.py') if '__pycache__' not in p.parts)
 out=R/('restart-extra-'+agent+'.txt');out.write_text('\n'.join(sorted(set(files)))+'\n');return out

def safe_restart(agent,plan,state):
 extra=snapshot_paths(agent,plan);env=safe_env(agent);env['MGS_GATEWAY_RESTART_EXTRA_SNAPSHOT_MANIFEST']=str(extra);env['MGS_GATEWAY_RESTART_EXPECTED_LAUNCHER']=plan['new_launcher'];env['HERMES_REPO']=plan['source']
 q=run([str(M/'scripts/mgs-gateway-restart-safe.sh'),'--agents',agent,'--reason','hermes-cutover-'+THREAD+'-'+agent,'--delay','2','--execute'],timeout=60,env=env,cwd=plan['source']);(R/('schedule-'+agent+'.log')).write_text(q.stdout+q.stderr)
 assert q.returncode==0,('safe scheduling failed',agent)
 match=re.search(r'log=(\S+)',q.stdout);assert match,('missing canonical finalizer receipt',agent)
 logfile=pathlib.Path(match.group(1));state['agents'].setdefault(agent,{})['canonical_finalizer_log']=str(logfile);save(STATE,state)
 deadline=time.monotonic()+420
 while time.monotonic()<deadline:
  text=logfile.read_text(errors='replace') if logfile.exists() else ''
  if 'DONE detached gateway restart finalizer' in text:break
  if any(x in text for x in ['ABORT ','FAILED ','Traceback (most recent call last)']):raise RuntimeError('canonical finalizer failed '+agent)
  time.sleep(2)
 else:raise TimeoutError('canonical finalizer deadline '+agent)
 actual=svc(agent);status=json.loads(pathlib.Path('/root/.hermes/profiles',agent,'gateway_state.json').read_text());assert actual['ActiveState']=='active' and actual['SubState']=='running' and actual['MainPID']!=plan['old_pids'][agent]
 assert status.get('code_sha')==plan['port'],('loaded runtime differs',agent)
 state['agents'][agent].update({'pid':actual['MainPID'],'ready':True,'code_sha':status.get('code_sha')});save(STATE,state)
 return actual

def validate_canary_database(db_path,session,marker,stdout):
 assert stdout.strip()==marker,'canary_final_response_mismatch'
 db=sqlite3.connect(pathlib.Path(db_path).as_uri()+'?mode=ro',uri=True,timeout=10);db.row_factory=sqlite3.Row
 try:rows=db.execute('SELECT role,content,tool_call_id,tool_calls,tool_name FROM messages WHERE session_id=? ORDER BY id',(session,)).fetchall()
 finally:db.close()
 calls={}
 for row in rows:
  if row['tool_calls']:
   toolcalls=json.loads(row['tool_calls']) if isinstance(row['tool_calls'],str) else row['tool_calls']
   for call in toolcalls or []:
    if call.get('function',{}).get('name')=='honcho_profile':calls[call.get('id')]=True
 assert calls,'honcho_profile_tool_call_missing'
 matched=0
 for row in rows:
  if row['role']=='tool' and (row['tool_call_id'] in calls or row['tool_name']=='honcho_profile'):
   text=row['content'] or ''
   try:value=json.loads(text) if isinstance(text,str) else text
   except (ValueError,TypeError):value={'text':text}
   if isinstance(value,dict):assert not value.get('is_error') and not value.get('error') and value.get('success') is not False,'honcho_tool_result_error'
   assert not str(text).lower().startswith(('error:','tool error:')),'honcho_tool_result_error';matched+=1
 assert matched,'honcho_profile_tool_result_missing'
 return {'honcho_profile_calls':len(calls),'honcho_successful_results':matched,'exact_response':True}

def real_canary(agent,plan,state):
 folder=R/'canaries'/agent;folder.mkdir(parents=True,exist_ok=True);marker='MGS-CANARY-'+agent+'-29a61cb7'
 prompt=('Validação técnica autorizada do Hermes. Faça exatamente uma chamada honcho_profile(peer="user"). Não chame outras ferramentas, não altere arquivos, não salve conclusões e não execute operações MGS. Não reproduza nenhum dado retornado. Após a chamada bem-sucedida, responda somente '+marker+'.')
 environment=proc_env(state['agents'][agent]['pid']);environment.update(HOME='/root',HERMES_HOME=str(pathlib.Path('/root/.hermes/profiles',agent)),TMPDIR=str(SCRATCH/'tmp'),TMP=str(SCRATCH/'tmp'),TEMP=str(SCRATCH/'tmp'))
 for attempt in [1,2]:
  usage=folder/('usage-'+str(attempt)+'.json');cmd=[plan['new_launcher'],'-p',agent,'-z',prompt,'--toolsets','memory','--usage-file',str(usage)];start=time.monotonic()
  q=run(cmd,timeout=240,env=environment,cwd=plan['source']);(folder/('stdout-'+str(attempt)+'.txt')).write_text(q.stdout);(folder/('stderr-'+str(attempt)+'.txt')).write_text(q.stderr)
  try:
   assert q.returncode==0,'canary_exit_nonzero';data=json.loads(usage.read_text());assert data.get('session_id'),'canary_session_id_missing';assert data.get('completed') is not False and not data.get('partial') and not data.get('interrupted'),'canary_incomplete'
   proof=validate_canary_database(pathlib.Path('/root/.hermes/profiles',agent,'state.db'),data['session_id'],marker,q.stdout)
   proof.update({'exit_code':0,'session_id':data['session_id'],'model':data.get('model'),'provider':data.get('provider'),'seconds':round(time.monotonic()-start,2),'attempt':attempt,'usage_file':str(usage)});state['agents'][agent]['canary']=proof;save(STATE,state);return
  except Exception as error:
   state['agents'][agent].setdefault('canary_failures',[]).append({'attempt':attempt,'reason':str(error),'exit_code':q.returncode});save(STATE,state)
   # Read-only validation may be safely repeated once, but never reauthenticate or change provider.
   if attempt==2:raise RuntimeError('real_canary_failed '+agent+' '+str(error)) from error
   time.sleep(8)

def restore_skills(plan,state):
 applied=set(state.get('applied_paths',[]));moved=BACKUP/'rollback-created-files'
 for row in reversed(plan['skill_entries']):
  if row['path'] not in applied:continue
  dest=pathlib.Path(row['path']);assert sha(dest)==row['after_sha256'],('rollback refuses concurrent skill change',row['path'])
  if row['before_sha256'] is None:
   target=moved/row['profile']/row['relative'];target.parent.mkdir(parents=True,exist_ok=True);assert not target.exists();os.replace(dest,target)
  else:
   source=BACKUP/'skills-before-cutover'/row['profile']/row['relative'];assert sha(source)==row['before_sha256'];temp=SCRATCH/('restore-'+uuid.uuid4().hex);shutil.copy2(source,temp);os.replace(temp,dest);assert sha(dest)==row['before_sha256']

def rollback(plan,state):
 set_state(state,'rolling_back');affected=list(state.get('agents',{}))
 for agent in reversed(affected):
  q=run(['systemctl','stop',agent+'-gateway.service'],timeout=370);assert q.returncode==0
 atomic_launcher(plan['old_launcher']);restore_skills(plan,state)
 # Schema32 is unchanged; retain current conversations and OAuth refreshes. No DB/auth restore.
 for agent in affected:
  q=run([str(M/'scripts/mgs-gateway-restart-safe.sh'),'--agents',agent,'--reason','hermes-rollback-'+THREAD+'-'+agent,'--delay','2','--execute'],timeout=60,env=safe_env(agent),cwd=plan['old_source']);assert q.returncode==0
  match=re.search(r'log=(\S+)',q.stdout);assert match;log=pathlib.Path(match.group(1));deadline=time.monotonic()+420
  while time.monotonic()<deadline:
   text=log.read_text(errors='replace') if log.exists() else ''
   if 'DONE detached gateway restart finalizer' in text:break
   if any(x in text for x in ['ABORT ','FAILED ']):raise RuntimeError('rollback readiness failed '+agent)
   time.sleep(2)
  else:raise TimeoutError('rollback readiness timeout '+agent)
  assert svc(agent)['ActiveState']=='active'
 set_state(state,'rolled_back_validated',rollback_profiles=affected,current_runtime=plan['old_port'])

def update_inventory(state,plan):
 for _ in range(3):
  path=M/'data/infra-inventory.json';raw=path.read_bytes();doc=json.loads(raw);items=doc['runtime_artifacts'];key='zeus-hermes-activation-'+THREAD;rows=[x for x in items if isinstance(x,dict) and x.get('id')==key];assert len(rows)<=1
  row=rows[0] if rows else {'id':key,'type':'hermes_authorized_runtime_activation','agent':'zeus','thread_id':THREAD,'authority_message_id':AUTHORITY}
  row.update({'status':state['status'],'updated_at':now(),'evidence':str(STATE),'source':plan['source'],'target':plan['target'],'port':plan['port'],'report_message_id':plan['report_message_id'],'gateway_results':{a:{'pid':v.get('pid'),'ready':v.get('ready'),'code_sha':v.get('code_sha'),'canary_pass':bool(v.get('canary'))} for a,v in state.get('agents',{}).items()}})
  if not rows:items.append(row)
  temp=SCRATCH/('inventory-'+uuid.uuid4().hex+'.json');temp.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n')
  if path.read_bytes()!=raw:continue
  os.replace(temp,path);readback=json.loads(path.read_text());assert any(isinstance(x,dict) and x.get('id')==key and x.get('status')==state['status'] for x in readback['runtime_artifacts']);return
 raise RuntimeError('concurrent inventory publication did not converge')

def checkpoint(state,plan):
 q=run(['python3',str(M/'scripts/mgs-knowledge-control.py'),'checkpoint-upsert','--id','ZEUS-HERMES-ACTIVATE-'+THREAD,'--agent','zeus','--thread-id',THREAD,'--objective','Ativação autorizada Hermes29a61cb7/afbd6248 e196arquivos de skills;sem exclusões/credenciais/sistema','--state',state['status'],'--next-step','Nenhum no corte autorizado;commits posteriores são outro lote. Preservar backups e rollback;sem limpeza autorizada.' if state['status']=='activated_validated' else 'Recuperação registrada;ler execution-state.json e não repetir efeitos já concluídos.','--source',str(STATE)+';authority:'+AUTHORITY+';report:'+plan['report_message_id']],timeout=60);assert q.returncode==0,'checkpoint publication failed'

def close_report(state,plan):
 mid=plan['report_message_id'];path='/channels/1498132022634483894/messages/'+mid;old=api('GET',path);assert old['author']['id']==BOT and old.get('content','')==''
 embeds=old.get('embeds',[]);assert len(embeds)==1;embed=embeds[0];embed.pop('type',None)
 outcome='ATIVADO E VALIDADO' if state['status']=='activated_validated' else state['status'].upper()
 fields=[x for x in embed.get('fields',[]) if x['name'] not in ['Resultado validado','Horário']]
 fields.extend([{'name':'Resultado validado','value':outcome+' | '+', '.join(a+':'+str(v.get('pid','-'))+' canary='+str(bool(v.get('canary'))) for a,v in state.get('agents',{}).items())+' | evidence='+str(STATE),'inline':False},{'name':'Horário','value':now(),'inline':True}]);embed['fields']=fields
 api('PATCH',path,{'content':'','embeds':[embed],'allowed_mentions':{'parse':[],'users':[],'roles':[]}});actual=api('GET',path);assert actual.get('content','')=='' and any(x['name']=='Resultado validado' and outcome in x['value'] for x in actual['embeds'][0]['fields']);state['report_readback_verified']=True;save(STATE,state)

def notify_origin(state,plan):
 if state['status']=='activated_validated':
  body=('**Hermes atualizado e validado.**\n\n'
        '- Corte `29a61cb7`, port MGS `afbd6248`, ativo em **Ares, Atena e Zeus**.\n'
        '- Os três voltaram ao Discord com processos novos e passaram nos canários reais de **Sol/Codex e Honcho**.\n'
        '- Sincronização autorizada: **196 arquivos de skills**, com hashes conferidos e regras MGS preservadas.\n'
        '- Backups e runtime anterior mantidos. Nenhuma exclusão, reboot da VPS ou alteração de credenciais/budget.\n\n'
        '**Efeito prático:** melhorias de estabilidade em entrega/continuidade, agendamentos e compactação, preservando as customizações MGS.\n\n'
        'Inventário, checkpoint e REPORT-INFRA atualizados e conferidos. Commits posteriores ao corte ficam para outro lote.\n\n'
        '**Observação:** root/default já estava sem Codex antes do corte; não foi alterado. Os três agentes estão autenticados e validados. Disco: '+str(round(state['disk']['used']/state['disk']['total']*100,1))+'% ocupado; '+str(round(state['disk']['free']/2**30,1))+' GiB livres. Backups preservados; limpeza fora do escopo.')
 else:
  body=('**A atualização não foi concluída.**\n\n'+('O runtime anterior foi restabelecido e os gateways afetados voltaram ao Discord. Nenhum histórico ou credencial foi restaurado por cima de dados novos.' if state['status']=='rolled_back_validated' else 'A execução parou no gate de segurança; o estado exato está preservado no checkpoint, sem repetir etapas.')+'\n\nEtapa: **'+state.get('failed_stage','preflight')+'**. Diagnóstico operacional: '+state.get('diagnostic_category','validação não atendida; causa-raiz requer a evidência privada')+'.\n\nNão ampliei o corte, não alterei credenciais e não apaguei backups. Evidência: `execution-state.json` desta atualização.')
 if state.get('origin_message_id'):
  actual=api('GET','/channels/'+THREAD+'/messages/'+state['origin_message_id']);assert actual.get('content')==body;state['origin_delivery_verified']=True;save(STATE,state);return
 # Recover a landed prior delivery rather than blindly duplicating an ambiguous POST.
 for message in api('GET','/channels/'+THREAD+'/messages?limit=50'):
  if str(message.get('author',{}).get('id'))==BOT and message.get('content')==body and int(message['id'])>int(state.get('handoff_message_id',AUTHORITY)):
   state['origin_message_id']=message['id'];save(STATE,state);actual=api('GET','/channels/'+THREAD+'/messages/'+message['id']);assert actual.get('content')==body;state['origin_delivery_verified']=True;save(STATE,state);return
 result=api('POST','/channels/'+THREAD+'/messages',{'content':body,'embeds':[],'components':[],'allowed_mentions':{'parse':[],'users':[],'roles':[]}});state['origin_message_id']=result['id'];save(STATE,state);actual=api('GET','/channels/'+THREAD+'/messages/'+result['id']);assert actual.get('content')==body;state['origin_delivery_verified']=True;save(STATE,state)

def readonly_auth_observation(plan):
 code='import json;from hermes_cli.auth import get_codex_auth_status;s=get_codex_auth_status();print(json.dumps({k:s.get(k) for k in ["logged_in","auth_mode","needs_refresh","rate_limited","error_code"]}))'
 result={}
 for agent in ['root',*ORDER]:
  env=safe_env(None if agent=='root' else agent)
  q=run([plan['python'],'-c',code],timeout=30,env=env,cwd=plan['source']);assert q.returncode==0,'read-only auth observer failed '+agent
  result[agent]=json.loads(q.stdout)
 return result

def execute(plan,state):
 preflight(plan);audit('hermes_cutover_started',target=plan['target'],port=plan['port'],handoff_message_id=state['handoff_message_id'])
 for agent in ORDER:
  set_state(state,'activating_'+agent,current_agent=agent);verify_static(plan);verify_skill_inputs(plan,state)
  state['agents'].setdefault(agent,{})['old_pid']=plan['old_pids'][agent];save(STATE,state)
  q=run(['systemctl','stop',agent+'-gateway.service'],timeout=370);assert q.returncode==0,'graceful stop failed '+agent
  fresh_profile_backup(agent,state);apply_skills(agent,plan,state)
  if pathlib.Path('/root/.local/bin/hermes').resolve()!=pathlib.Path(plan['new_launcher']).resolve():atomic_launcher(plan['new_launcher'])
  safe_restart(agent,plan,state);real_canary(agent,plan,state);audit('hermes_cutover_agent_validated',agent=agent,pid=state['agents'][agent]['pid'],source=plan['port'],honcho=True)
 for agent in ORDER:
  service=svc(agent);assert service['ActiveState']=='active' and service['SubState']=='running';assert service['MainPID']==state['agents'][agent]['pid'];assert state['agents'][agent].get('canary')
 for agent in ORDER:
  for name,digest in plan['profile_config_hashes'][agent].items():assert sha(pathlib.Path('/root/.hermes/profiles',agent,name))==digest,('post-cutover profile drift',agent,name)
 for row in plan['skill_entries']:assert sha(row['path'])==row['after_sha256'],('post-cutover skill drift',row['path'])
 assert len(state['applied_paths'])==len(plan['skill_entries'])
 state['post_auth_observation']=readonly_auth_observation(plan)
 assert all(state['post_auth_observation'][agent].get('logged_in') for agent in ORDER),'named profile auth observation failed'
 usage=shutil.disk_usage('/');state['disk']={'total':usage.total,'used':usage.used,'free':usage.free}
 save(STATE,state)
 set_state(state,'activated_validated',completed_at=now(),runtime=plan['port'],skills_applied=len(state['applied_paths']),current_agent=None);audit('hermes_cutover_validated',port=plan['port'],profiles=ORDER,skills=196)

def self_test():
 folder=SCRATCH/('validator-fixture-'+uuid.uuid4().hex);folder.mkdir();p=folder/'synthetic.db';db=sqlite3.connect(p);db.execute('CREATE TABLE messages(id INTEGER PRIMARY KEY, session_id TEXT,role TEXT,content TEXT,tool_call_id TEXT,tool_calls TEXT,tool_name TEXT)');db.execute('INSERT INTO messages VALUES(1,?,?,?,?,?,?)',('synthetic','assistant','',None,json.dumps([{'id':'fixture-call','function':{'name':'honcho_profile'}}]),None));db.execute('INSERT INTO messages VALUES(2,?,?,?,?,?,?)',('synthetic','tool',json.dumps({'success':True,'fixture':True}),'fixture-call',None,'honcho_profile'));db.commit();db.close();assert validate_canary_database(p,'synthetic','FIXTURE','FIXTURE')['exact_response']
 try:validate_canary_database(p,'synthetic','FIXTURE','WRONG')
 except AssertionError:pass
 else:raise AssertionError('negative fixture did not fail')
 print('Synthetic canary parser positive/negative tests PASS; no remote model call')

def close_all(state,plan):
 for attempt in range(4):
  try:
   update_inventory(state,plan);checkpoint(state,plan);close_report(state,plan);notify_origin(state,plan);audit('hermes_cutover_closed',status=state['status'],origin_message_id=state.get('origin_message_id'));state['closure_complete']=True;save(STATE,state);return
  except Exception:
   state['closure_error']=traceback.format_exc();state['closure_attempts']=attempt+1;save(STATE,state)
   if attempt==3:raise
   time.sleep(6)

def main():
 os.umask(0o077);a=argparse.ArgumentParser();a.add_argument('--preflight',action='store_true');a.add_argument('--self-test',action='store_true');a.add_argument('--wait-for-handoff',action='store_true');args=a.parse_args();SCRATCH.mkdir(parents=True,exist_ok=True);(SCRATCH/'tmp').mkdir(exist_ok=True)
 if args.self_test:self_test();return 0
 plan=load_plan()
 if not args.wait_for_handoff:print(json.dumps(preflight(plan)));return 0
 lock=(M/'data/hermes-activation-1567354570823172209.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);state=current_state()
 if state.get('status') in {'activated_validated','rolled_back_validated'}:
  if not state.get('closure_complete'):close_all(state,plan)
  return 0 if state['status']=='activated_validated' else 1
 try:
  preflight(plan);wait_handoff(plan,state);execute(plan,state)
 except Exception as error:
  state.update(failed_stage=state.get('status','preflight'),error_type=type(error).__name__,error=str(error),diagnostic_category=('canário real não passou' if 'canary' in str(error) else 'gate técnico de ativação não passou'));(R/'failure-private-trace.log').write_text(traceback.format_exc());save(STATE,state);audit('hermes_cutover_failed',stage=state['failed_stage'],error_type=type(error).__name__)
  if state.get('agents'):
   try:rollback(plan,state)
   except Exception:state['rollback_error']=traceback.format_exc();set_state(state,'blocked_rollback_incomplete')
  else:set_state(state,'blocked_before_any_gateway_change')
 close_all(state,plan)
 return 0 if state['status']=='activated_validated' else 1
if __name__=='__main__':sys.exit(main())
