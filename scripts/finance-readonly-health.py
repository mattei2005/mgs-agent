#!/usr/bin/env python3
"""Hourly read-only finance reconciliation. No login, DML or restart authority.
Rodolfo1556500454291148811. Uses one bounded SSH probe and exact Discord readback.
"""
import argparse,datetime,fcntl,hashlib,importlib.util,json,os,pathlib,shlex,sys,tempfile,time,urllib.request
ROOT=pathlib.Path('/root/mgs-agent');APP=ROOT/'apps/finance-system';STATE=ROOT/'data/finance-readonly-health-state.json';CHANNEL='1522444367292268565'
NODE='/home/mgsfinance/runtime/node-v22.23.2-linux-x64/bin/node';TARGET='/home/mgsfinance/releases/pg-auth-1545934831664242748'
PROBE="""import {openPostgres} from './storage.mjs';import {managerView} from './manager-view.mjs';const db=await openPostgres({options:'-c default_transaction_read_only=on -c statement_timeout=30000'});const checks=[],failures=[];try{const rows=(await db.query(\"SELECT id FROM scenarios WHERE id LIKE 'workspace-%' ORDER BY id\")).rows;if(!rows.length)throw Error('no_workspaces');for(const {id}of rows){const s=(await db.query('SELECT * FROM scenarios WHERE id=$1',[id])).rows[0];for(const key of ['icaro','isliago','joe','kelly','nicolas']){try{const r=managerView(s,null,id.slice(10),key);if(r.summary_control&&!r.summary_control.pass)throw Error('reconciliation');checks.push({period:id.slice(10),manager:key,revision:s.revision});}catch(e){failures.push({period:id.slice(10),manager:key,code:e.message.startsWith('Manager current block total mismatch:')?'manager_reconciliation':'view_failure'});}}}console.log(JSON.stringify({ok:!failures.length,expected:rows.length*5,checked:checks.length+failures.length,passed:checks.length,failures}));}finally{await db.close();}"""
def collect():
 sys.path.insert(0,str(ROOT/'scripts'));from mgs_google_workspace_auth import load_env;load_env()
 sys.path.insert(0,str(APP/'deploy'));from runcloud_ops import ssh
 sys.path.insert(0,str(APP));from finance_release_guard import lease
 with lease(APP,timeout=8,recover_pending=False):
  raw=ssh('sudo -n -u mgsfinance sh -c '+shlex.quote('cd '+TARGET+' && '+NODE+' --input-type=module'),input_data=PROBE.encode(),timeout=90)
 r=json.loads(raw)
 if not isinstance(r.get('expected'),int) or r['expected']<=0 or r.get('checked')!=r['expected'] or r.get('passed',0)+len(r.get('failures',[]))!=r['checked']:raise ValueError('coverage')
 return r

def payload(result,recovery=False):
 failures=result.get('failures',[]);detail='\n'.join(x['period']+' · '+x['manager']+' · '+x['code'] for x in failures[:10]) or 'Consulta de produção indisponível; nenhuma alteração financeira executada.'
 return {'content':'' if recovery else '<@344196393512075265>','allowed_mentions':{'parse':[],'users':[] if recovery else ['344196393512075265'],'roles':[],'replied_user':False},'embeds':[{'title':'Financeiro — verificação recuperada' if recovery else 'Financeiro — verificação bloqueada','color':3066993 if recovery else 15158332,'fields':[{'name':'Resultado','value':f"{result.get('passed',0)}/{result.get('expected',0)} combinações válidas" if recovery else detail,'inline':False},{'name':'Validação','value':'Módulo implantado + banco PostgreSQL em somente leitura; serviços e regras não foram alterados.','inline':False},{'name':'Ação','value':'Recuperação confirmada; operação normal.' if recovery else 'Consulta repetida. Preservada a trava financeira; investigar causa antes de corrigir valores. Origem: thread1545426987756298340.','inline':False}]}]}

def send_notice(body,requester=None):
 if requester is None:
  spec=importlib.util.spec_from_file_location('finance_notice',APP/'finance-notifications.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);token=m.dotenv_values('/root/.hermes/profiles/zeus/.env').get('DISCORD_BOT_TOKEN');assert token,'Discord credential missing'
  def requester(path,data=None):
   req=urllib.request.Request('https://discord.com/api/v10'+path,data=json.dumps(data).encode() if data is not None else None,headers={'Authorization':'Bot '+token,'Content-Type':'application/json','User-Agent':'MGS-Finance-ReadOnly/1.0'},method='POST' if data is not None else 'GET')
   with urllib.request.urlopen(req,timeout=15) as f:return json.load(f)
 posted=requester('/channels/'+CHANNEL+'/messages',body);mid=posted['id'];read=requester('/channels/'+CHANNEL+'/messages/'+mid)
 if read.get('channel_id')!=CHANNEL or read.get('content','')!=body['content'] or len(read.get('embeds',[]))!=1 or read['embeds'][0].get('title')!=body['embeds'][0]['title']:raise ValueError('Discord readback mismatch')
 return {'message_id':mid,'channel_id':CHANNEL,'readback':True}

def transition(old,result,send):
 now=datetime.datetime.now(datetime.timezone.utc).isoformat();new={**old,'last_check':now,'result':result,'authority':'1556500454291148811','last_status':'ok' if result.get('ok') else 'failed'}
 if result.get('ok'):
  if old.get('alert_signature'):new['last_notice']=send(payload(result,True));new['alert_signature']=None
  new['failure_streak']=0;new['last_success']=now
 else:
  signature=hashlib.sha256(json.dumps(result.get('failures',[]),sort_keys=True).encode()).hexdigest();new['failure_streak']=old.get('failure_streak',0)+1
  if signature!=old.get('alert_signature'):new['last_notice']=send(payload(result));new['alert_signature']=signature
 return new

def persist(path,data):
 fd,tmp=tempfile.mkstemp(prefix=path.name+'.',dir=path.parent)
 with os.fdopen(fd,'w') as f:json.dump(data,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 os.replace(tmp,path)
 assert json.loads(path.read_text())==data

def main():
 p=argparse.ArgumentParser();p.add_argument('--check-only',action='store_true');args=p.parse_args()
 with open('/var/lock/mgs-finance-readonly-health.lock','a') as lock:
  try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:return
  def attempt():
   try:return collect()
   except Exception as e:return {'ok':False,'expected':0,'checked':0,'passed':0,'failures':[{'period':'unknown','manager':'all','code':'probe_'+type(e).__name__}]}
  result=attempt()
  if not result['ok']:time.sleep(2);result=attempt()
  if args.check_only:print(json.dumps(result));return
  old=json.loads(STATE.read_text()) if STATE.exists() else {};new=transition(old,result,send_notice);persist(STATE,new);print(json.dumps({'status':new['last_status'],'passed':result['passed'],'expected':result['expected'],'financial_writes':0,'notice_sent':new.get('last_notice')!=old.get('last_notice')}))
if __name__=='__main__':main()
