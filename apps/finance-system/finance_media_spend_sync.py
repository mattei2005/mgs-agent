"""Daily MGS ad-spend sync. Eastern9am (09:03+25s); API-first discovery, safe account/site registration and current month through yesterday."""
import pathlib,sys,json,datetime,fcntl,os,shlex,hashlib,base64,argparse,subprocess
from zoneinfo import ZoneInfo
ROOT=pathlib.Path(__file__).resolve().parent;DATA=pathlib.Path('/root/mgs-agent/data');STATE=DATA/'finance-media-spend-state.json';LOCK=ROOT/'private/media-spend-sync.lock';TZ=ZoneInfo('America/New_York');THREAD='1545426987756298340';AUTH='1547015219325444107'
sys.path.insert(0,str(ROOT/'deploy'));from runcloud_ops import ssh
from finance_spend_sources import collect_api_first,dates
from spend_report import render_report
TARGET='/home/mgsfinance/releases/pg-auth-1545934831664242748';NODE='/home/mgsfinance/runtime/node-v22.23.2-linux-x64/bin/node';PG='sudo -n -u mgs_pg env LD_LIBRARY_PATH=/opt/mgs-postgresql18/usr/lib/x86_64-linux-gnu /opt/mgs-postgresql18/usr/lib/postgresql/18/bin/psql -h /run/mgs-postgresql18 -U mgs_pg -v ON_ERROR_STOP=1 -At -d mgs_finance -c '
def window(at):
 end=at.astimezone(TZ).date()-datetime.timedelta(days=1);return end.replace(day=1).isoformat(),end.isoformat()
def pipeline_window(source_date,at):
 end=datetime.date.fromisoformat(source_date);assert end<at.astimezone(TZ).date();return end.replace(day=1).isoformat(),end.isoformat()
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
 rendered=render_report(report);payload={'content':'<@344196393512075265>' if rendered['attention'] else '', 'allowed_mentions':{'parse':[],'users':['344196393512075265'],'roles':[],'replied_user':False},'embeds':[{'title':rendered['title'],'description':rendered['body'],'color':15105570 if rendered['attention'] else 3066993}]}
 payload['nonce']=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()[:24];payload['enforce_nonce']=True
 child_env={k:v for k,v in os.environ.items() if k not in ['DISCORD_BOT_TOKEN','MGS_DISCORD_BOT_TOKEN_OVERRIDE','MGS_DISCORD_API_URL_OVERRIDE','MGS_DISCORD_BOT_ENV','MGS_DRY_RUN']};child_env['MGS_DISCORD_BOT_ENV']='/root/.hermes/profiles/zeus/.env'
 p=subprocess.run(['python3','/root/mgs-agent/scripts/discord-bot-post.py','--channel-id',THREAD],input=json.dumps(payload),text=True,capture_output=True,timeout=60,env=child_env)
 if p.returncode:raise RuntimeError('Discord report delivery failed')
 import re
 match=re.search(r'message_id=(\d+)',p.stdout);assert match;return verify_notice(match[1],payload)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--scheduled',action='store_true');ap.add_argument('--pipeline-date');ap.add_argument('--since');ap.add_argument('--until');ap.add_argument('--collection-file');ap.add_argument('--dry-run',action='store_true');ap.add_argument('--notify',action='store_true');args=ap.parse_args();now=datetime.datetime.now(TZ);daily=bool(args.scheduled or args.pipeline_date)
 if args.scheduled and now.hour!=9:return
 if args.pipeline_date and (args.since or args.until):raise ValueError('Pipeline date cannot be combined with a manual window')
 if daily and args.collection_file:raise ValueError('Daily execution reuse forbidden')
 start,end=pipeline_window(args.pipeline_date,now) if args.pipeline_date else ((args.since,args.until) if args.since or args.until else window(now));dates(start,end);assert datetime.date.fromisoformat(end)<now.date();state=json.loads(STATE.read_text()) if STATE.exists() else {};run=now.strftime('%Y%m%dT%H%M%S%z');folder=ROOT/'private/media-spend-runs'/run;folder.mkdir(parents=True,exist_ok=True,mode=0o700);step='preflight';report=None
 with LOCK.open('a') as lock:
  try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:return
  if daily and state.get('blocked_after_five'):return
  if daily and state.get('last_scheduled_day')==now.date().isoformat() and state.get('last_status')=='ok' and state.get('last_until','')>=end:return
  try:
   from mgs_google_workspace_auth import load_env
   load_env();step='source_collection'
   if args.collection_file:
    report_source=json.loads(pathlib.Path(args.collection_file).read_text());assert report_source['since']==start and report_source['until']==end and report_source['schema']=='api-first-1';save(folder/'collection.json',report_source)
   else:report_source=collect_api_first(start,end,folder/'sources');save(folder/'collection.json',report_source)
   step='dash_import'
   with (ROOT/'private/quote-sync.lock').open('a') as qlock:
    fcntl.flock(qlock,fcntl.LOCK_EX);result=ssh('sudo -n -u mgsfinance '+NODE+' '+TARGET+'/api-spend-cli.mjs mgs_finance'+(' --dry-run' if args.dry_run else ''),json.dumps(report_source).encode(),timeout=420)
   report=json.loads(result);assert report.get('pass') and (args.dry_run or report.get('readback'));save(folder/'result.json',report)
   if not args.dry_run:
    backup=report.get('backup');assert backup and backup['verified'];raw=base64.b64decode(ssh('sudo -n base64 -w0 '+shlex.quote(backup['path']),timeout=180),validate=True);assert hashlib.sha256(raw).hexdigest()==backup['sha256'];p=folder/'before.json.gz';p.write_bytes(raw);p.chmod(0o600)
    step='record_state';ok=not report.get('source_errors') and not report.get('discovery_errors') and not report.get('api_query_errors');streak=0 if ok else state.get('failure_streak',0)+1
    updated={**state,'authority':AUTH,'timezone':str(TZ),'last_run_at':now.isoformat(),'last_until':end,'last_status':'ok' if ok else 'partial','failure_streak':streak,'blocked_after_five':streak>=5,'last_failure':None if ok else state.get('last_failure'),'last_report_path':str(folder/'result.json'),'last_collection_path':str(folder/'collection.json'),'last_missing_ids':[a['platform']+'|'+a['account_id'] for a in report.get('missing_accounts',[])],'last_scheduled_day':now.date().isoformat() if daily else state.get('last_scheduled_day'),'last_trigger':'pipeline' if args.pipeline_date else ('schedule' if args.scheduled else 'manual'),'last_backup':str(folder/'before.json.gz')};save(STATE,updated)
   rendered=render_report(report)
   if not args.dry_run and (args.notify or daily):
    step='notification';proof=notice(report);save(folder/'notification.json',proof);current=json.loads(STATE.read_text());save(STATE,{**current,'last_notice_signature':rendered['signature'],'last_notice':proof})
   print(json.dumps({k:v for k,v in report.items() if k not in ['missing_accounts','changes','api_unavailable']}|{'missing_account_count':len(report.get('missing_accounts',[])),'evidence':str(folder)},ensure_ascii=False))
  except Exception as e:
   failure={'pass':False,'since':start,'until':end,'step':step,'error':type(e).__name__,'detail':str(e)[:500],'evidence':str(folder)};save(folder/'failure.json',failure)
   if not args.dry_run:
    previous=json.loads(STATE.read_text()) if STATE.exists() else state;streak=previous.get('failure_streak',0)+1;save(STATE,{**previous,'authority':AUTH,'last_run_at':now.isoformat(),'last_status':'failed','failure_streak':streak,'blocked_after_five':streak>=5,'last_failure':failure})
   if daily or args.notify:
    try:save(folder/'failure-notification.json',notice(failure))
    except Exception:pass
   print(json.dumps(failure));raise SystemExit(1)
if __name__=='__main__':main()
