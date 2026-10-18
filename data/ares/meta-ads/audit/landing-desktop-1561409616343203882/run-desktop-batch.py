"""Bounded same-scope desktop batch supervisor; all output stays local."""
import os,sys,json,time,subprocess,signal,sqlite3
from pathlib import Path
ROOT=Path('/root/mgs-agent/data/ares/meta-ads/audit/landing-desktop-1561409616343203882')
S=json.loads((ROOT/'batch-scope.json').read_text());sid=os.environ['HERMES_SESSION_ID'];py=str(Path('/root/.local/bin/hermes').resolve().parent/'python');child=None;stopping=False

def stop(*_):
 global stopping
 stopping=True
 if child and child.poll() is None:child.send_signal(signal.SIGTERM)
signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)

def states():
 c=sqlite3.connect('file:/root/mgs-agent/data/ares/meta-ads/landing-followup/queue.sqlite3?mode=ro',uri=True);c.row_factory=sqlite3.Row;c.execute('PRAGMA query_only=ON');out=[]
 for x in S['jobs']:
  for r in c.execute('select idx,state,attempt from links where job=? order by idx',(x['key'],)):out.append(dict(r,job=x['key']))
 c.close();return out

try:
 results=[]
 for run in range(1,18):
  links=states()
  if all(x['state'] in {'PASSED','RESOLVED_BY_OPERATOR','REVIEW_REQUIRED'} for x in links):break
  if stopping or time.time()>=S['deadline']:break
  args=[py,'/root/mgs-agent/scripts/ares-direct-traffic-batch-observe.py','--scope',str(ROOT/'batch-scope.json'),'--owner',S['owner'],'--pc1-session-id',sid]
  log=ROOT/('batch-run-'+str(run)+'.log')
  with log.open('w') as f:
   child=subprocess.Popen(args,stdout=f,stderr=subprocess.STDOUT,env=os.environ.copy());code=child.wait()
  messages=[]
  for line in log.read_text().splitlines():
   try:d=json.loads(line)
   except ValueError:continue
   if isinstance(d,dict) and d.get('state'):messages.append(d)
  result=messages[-1] if messages else {'state':'MISSING_RUN_RESULT'};results.append(result);(ROOT/'batch-results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
  if code or result['state'] in {'BATCH_TECHNICAL_DIAGNOSIS','BATCH_RECOVERY_REQUIRED','MAPPING_REQUIRED','MISSING_RUN_RESULT','WAITING_PC1','YIELD_OLDER_DUE_WORK','PAUSED_AT_SAFE_BOUNDARY'}:break
  if result['state']=='AUTOMATIC_RECOVERY_COOLDOWN':
   due=float((result.get('transition') or {}).get('due',time.time()+60));time.sleep(max(0,min(65,due-time.time()+.5)))
  elif result['state']=='FINITE_PASS_SETTLED' and not all(x['state'] in {'PASSED','RESOLVED_BY_OPERATOR','REVIEW_REQUIRED'} for x in states()):
   # A bounded new cohort can cover later jobs in the already frozen scope.
   continue
  elif result['state'] not in {'AUTOMATIC_RECOVERY_COOLDOWN','INITIAL_OR_FINAL_IN_PROGRESS','FINAL_RETRY_SCHEDULED','AUTOMATIC_RECOVERY_SCHEDULED','FINITE_PASS_SETTLED'}:break
 links=states();counts={s:sum(x['state']==s for x in links) for s in sorted({x['state'] for x in links})}
 out={'authority_message_id':'1561409616343203882','results_count':len(results),'last_state':results[-1]['state'] if results else 'ALREADY_TERMINAL','total_links_in_human_groups':len(links),'states':counts,'all_terminal':all(x['state'] in {'PASSED','RESOLVED_BY_OPERATOR','REVIEW_REQUIRED'} for x in links),'all_passed':all(x['state']=='PASSED' for x in links),'links':links}
 (ROOT/'batch-verification.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in out.items() if k!='links'},ensure_ascii=False),flush=True)
finally:
 subprocess.run(['systemctl','start','ares-landing-followup.timer'],capture_output=True,text=True,timeout=30)
