"""Daily MGS ad-spend sync. Eastern7am; current month through yesterday, exact registered IDs only."""
import pathlib,sys,json,datetime,fcntl,os,shlex,hashlib,base64,argparse,subprocess
from zoneinfo import ZoneInfo
ROOT=pathlib.Path(__file__).resolve().parent;DATA=pathlib.Path('/root/mgs-agent/data');STATE=DATA/'finance-media-spend-state.json';LOCK=ROOT/'private/media-spend-sync.lock';TZ=ZoneInfo('America/New_York');THREAD='1545426987756298340';AUTH='1546991137171181578'
sys.path.insert(0,str(ROOT/'deploy'));from runcloud_ops import ssh
from finance_spend_sources import collect,dates
TARGET='/home/mgsfinance/releases/pg-auth-1545934831664242748';NODE='/home/mgsfinance/runtime/node-v22.23.2-linux-x64/bin/node';PG='sudo -n -u mgs_pg env LD_LIBRARY_PATH=/opt/mgs-postgresql18/usr/lib/x86_64-linux-gnu /opt/mgs-postgresql18/usr/lib/postgresql/18/bin/psql -h /run/mgs-postgresql18 -U mgs_pg -v ON_ERROR_STOP=1 -At -d mgs_finance -c '
def window(at):
 end=at.astimezone(TZ).date()-datetime.timedelta(days=1);return end.replace(day=1).isoformat(),end.isoformat()
def save(path,data):
 path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_name(path.name+'.pending');tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2));tmp.chmod(0o600);os.replace(tmp,path)
def verify_notice(message_id,payload):
 import importlib.util,urllib.request
 spec=importlib.util.spec_from_file_location('finance_notices',ROOT/'finance-notifications.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);token=module.dotenv_values('/root/.hermes/profiles/zeus/.env').get('DISCORD_BOT_TOKEN');assert token
 req=urllib.request.Request('https://discord.com/api/v10/channels/'+THREAD+'/messages/'+message_id,headers={'Authorization':'Bot '+token,'User-Agent':'MGS-Finance-Spend/1.0'})
 with urllib.request.urlopen(req,timeout=15) as response:message=json.load(response)
 assert message['id']==message_id and message['channel_id']==THREAD and message['author']['id']=='1496296175014252634' and message['content']==payload['content']
 assert message['embeds'][0]['title']==payload['embeds'][0]['title'] and message['embeds'][0]['description']==payload['embeds'][0]['description']
 return {'message_id':message_id,'channel_id':THREAD,'readback':True}
def notice(report):
 title='Gastos de mídia · '+report.get('until','falha');totals=report.get('totals',{});text=' · '.join(c+' '+v for c,v in totals.items());missing=report.get('missing_accounts',[]);exceptions=report.get('exceptions',[])
 if report.get('pass'):body=f"{report['since']} a {report['until']}\n{report['recorded_accounts']} contas registradas · {report['rows']} dias/contas.\n{text}\nContas da plataforma ausentes no Dash: {len(missing)}. Vínculos/edições a revisar: {len(exceptions)}.\nLista completa: https://dash.mgsdigitalcorp.com/?view=accounts&period={report['period']}\nSem cadastro automático nem alteração de anúncios."
 else:body='A importação não foi confirmada. Valores anteriores preservados onde não houve confirmação. Etapa: '+report.get('step','desconhecida')+'; erro: '+report.get('error','indisponível')+'. Zeus deve investigar antes de reexecutar.'
 payload={'content':'<@344196393512075265>' if missing or exceptions or not report.get('pass') else '', 'allowed_mentions':{'parse':[],'users':['344196393512075265'],'roles':[],'replied_user':False},'embeds':[{'title':title,'description':body,'color':15105570 if missing or exceptions or not report.get('pass') else 3066993}]}
 p=subprocess.run(['/root/mgs-agent/scripts/discord-bot-post.py','--channel-id',THREAD],input=json.dumps(payload),text=True,capture_output=True,timeout=70)
 if p.returncode:raise RuntimeError('Discord report delivery failed')
 import re
 match=re.search(r'message_id=(\d+)',p.stdout);assert match;return verify_notice(match[1],payload)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--scheduled',action='store_true');ap.add_argument('--since');ap.add_argument('--until');ap.add_argument('--collection-file');ap.add_argument('--dry-run',action='store_true');ap.add_argument('--notify',action='store_true');args=ap.parse_args();now=datetime.datetime.now(TZ)
 if args.scheduled and now.hour!=7:return
 if args.scheduled and args.collection_file:raise ValueError('Scheduled reuse forbidden')
 start,end=(args.since,args.until) if args.since or args.until else window(now);dates(start,end);assert datetime.date.fromisoformat(end)<now.date();state=json.loads(STATE.read_text()) if STATE.exists() else {};run=now.strftime('%Y%m%dT%H%M%S%z');folder=ROOT/'private/media-spend-runs'/run;folder.mkdir(parents=True,exist_ok=True,mode=0o700);step='preflight';report=None
 with LOCK.open('a') as lock:
  try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:return
  if args.scheduled and state.get('blocked_after_five'):return
  if args.scheduled and state.get('last_scheduled_day')==now.date().isoformat() and state.get('last_status')=='ok':return
  try:
   from mgs_google_workspace_auth import load_env
   load_env();registry=json.loads(ssh(PG+shlex.quote("SELECT jsonb_build_object('revision',revision,'accounts',additions)||result FROM scenarios WHERE id='master-ad-accounts'")));save(folder/'registry.json',registry);step='source_collection'
   if args.collection_file:
    report_source=json.loads(pathlib.Path(args.collection_file).read_text());assert report_source['since']==start and report_source['until']==end and report_source['registry_revision']==registry['revision'];save(folder/'collection.json',report_source)
   else:report_source=collect(registry,start,end,folder/'sources');save(folder/'collection.json',report_source)
   step='dash_import'
   with (ROOT/'private/quote-sync.lock').open('a') as qlock:
    fcntl.flock(qlock,fcntl.LOCK_EX);result=ssh('sudo -n -u mgsfinance '+NODE+' '+TARGET+'/media-spend-cli.mjs mgs_finance'+(' --dry-run' if args.dry_run else ''),json.dumps(report_source).encode(),timeout=420)
   report=json.loads(result);assert report.get('pass') and (args.dry_run or report.get('readback'));save(folder/'result.json',report)
   if not args.dry_run:
    backup=report.get('backup');assert backup and backup['verified'];raw=base64.b64decode(ssh('sudo -n base64 -w0 '+shlex.quote(backup['path']),timeout=180),validate=True);assert hashlib.sha256(raw).hexdigest()==backup['sha256'];p=folder/'before.json.gz';p.write_bytes(raw);p.chmod(0o600)
    step='record_state';ok=not report.get('source_errors') and not report.get('discovery_errors');streak=0 if ok else state.get('failure_streak',0)+1
    updated={**state,'authority':AUTH,'timezone':str(TZ),'last_run_at':now.isoformat(),'last_until':end,'last_status':'ok' if ok else 'partial','failure_streak':streak,'blocked_after_five':streak>=5,'last_report_path':str(folder/'result.json'),'last_collection_path':str(folder/'collection.json'),'last_missing_ids':[a['platform']+'|'+a['account_id'] for a in report.get('missing_accounts',[])],'last_scheduled_day':now.date().isoformat() if args.scheduled else state.get('last_scheduled_day'),'last_backup':str(folder/'before.json.gz')};save(STATE,updated)
   if args.notify or args.scheduled:
    step='notification';proof=notice(report);save(folder/'notification.json',proof)
   print(json.dumps({k:v for k,v in report.items() if k not in ['missing_accounts','changes']}|{'missing_account_count':len(report.get('missing_accounts',[])),'evidence':str(folder)},ensure_ascii=False))
  except Exception as e:
   failure={'pass':False,'since':start,'until':end,'step':step,'error':type(e).__name__,'evidence':str(folder)};save(folder/'failure.json',failure)
   if not args.dry_run:
    previous=json.loads(STATE.read_text()) if STATE.exists() else state;streak=previous.get('failure_streak',0)+1;save(STATE,{**previous,'authority':AUTH,'last_run_at':now.isoformat(),'last_status':'failed','failure_streak':streak,'blocked_after_five':streak>=5,'last_failure':failure})
   if args.scheduled or args.notify:
    try:save(folder/'failure-notification.json',notice(failure))
    except Exception:pass
   print(json.dumps(failure));raise SystemExit(1)
if __name__=='__main__':main()
