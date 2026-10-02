"""Run one exact read-only consumer canary and return safe counters only."""
import argparse,json,os,re,signal,subprocess,time
from pathlib import Path
P=Path('/root/.hermes/profiles/zeus/cache/scratch/browser-budget-four-1555702597925470400')
PY='/root/.local/share/mgs/sb-venv/bin/python'; BASE='/root/mgs-agent/scripts/'
JOBS={
 'dtr':('dtr_sb_page_health_sync.lock',[BASE+'dtr-sb-page-health-sync.sh','--limit-users','1','--limit-accounts','1','--limit-pages','1']),
 'sms':('sync_sb_sms_revenue_daily.lock',['xvfb-run','-a',PY,BASE+'sync-sb-sms-revenue-daily.py','--fetch-only','--no-alert']),
 'revenue':('sync_sb_messenger_revenue_sheet.lock',['xvfb-run','-a',PY,BASE+'sync-sb-messenger-revenue-sheet.py','--dry-run','--no-alert']),
 'tokens':('monitor_sb_messenger_token_invalid.lock',['xvfb-run','-a',PY,BASE+'monitor-sb-messenger-token-invalid.py','--dry-run']),
}
args=argparse.ArgumentParser();args.add_argument('phase');args.add_argument('job',choices=JOBS);a=args.parse_args()
lock,cmd=JOBS[a.job];cmd=['flock','-n','/var/lock/'+lock,*cmd]
start=time.monotonic();proc=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,start_new_session=True)
try: out,err=proc.communicate(timeout=240)
except subprocess.TimeoutExpired:
 os.killpg(proc.pid,signal.SIGTERM)
 out,err=proc.communicate(timeout=15)
result={'phase':a.phase,'job':a.job,'exit_code':proc.returncode,'elapsed_seconds':round(time.monotonic()-start,3),'read_only_business':True}
decoder=json.JSONDecoder();roots=[]
for m in re.finditer(r'(?m)^\s*\{',out):
 try:d,end=decoder.raw_decode(out[m.start():].lstrip())
 except ValueError:continue
 if isinstance(d,dict):roots.append(d)
if roots:
 d=roots[-1]
 allowed=['ok','status','mode','target_date','sheet_active_users','matched_1p_users','sb_rows','sb_active_restricted_start','stats','writes','total_rows','rows','report_rows','company_count','publishers','matched_rows','sheet_named_rows','notifications','pages','alerts_seen','state_written','dry_run','post_count','pending_count','new_alerts','cursor_before','cursor_after','auth']
 result['consumer_result']={k:v for k,v in d.items() if k in allowed}
 result['result_keys']=list(d)
 result['error_count']=len(d.get('errors',[])) if isinstance(d.get('errors',[]),list) else None
 if d.get('error'):result['error']=d['error'] if len(str(d['error']))<150 else str(d['error'])[:150]
 result['pass']=proc.returncode==0 and d.get('ok') is not False and not result['error_count']
else:result['pass']=False
# Canonical xvfb-run intentionally merges the command's stderr into stdout.
result['budget_events']=[json.loads(s.removeprefix('BROWSER_BUDGET ')) for s in (out+'\n'+err).splitlines() if s.startswith('BROWSER_BUDGET ')]
if a.phase == 'post':
 result['admission_verified'] = [e['event'] for e in result['budget_events']] == ['queued', 'admitted', 'released'] and result['budget_events'][-1].get('outcome') == 'success'
 result['pass'] = result['pass'] and result['admission_verified']
if not result['pass']:
 result['error_types']=list(dict.fromkeys(re.findall(r'(?:RuntimeError|TimeoutError|ImportError|ModuleNotFoundError|PermissionError|KeyError|AttributeError|HTTPError)',out+'\n'+err)))
 result['http_statuses']=list(dict.fromkeys(re.findall(r'(?:response|HTTP|status)\s*(\d{3})',out+'\n'+err)))
 # Keep raw failure local/private; never project company or credential payloads.
 raw=P/(a.phase+'-'+a.job+'-failure-private.log');raw.write_text(out+'\n'+err);raw.chmod(0o600)
 result['private_failure_log']=str(raw)
(P/(a.phase+'-'+a.job+'.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False))
raise SystemExit(0 if result['pass'] else 1)
