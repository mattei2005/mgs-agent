import json, re, statistics, subprocess, datetime, os
from pathlib import Path
from collections import Counter
from zoneinfo import ZoneInfo
ROOT=Path('/root/mgs-agent'); ET=ZoneInfo('America/New_York')
OUT=ROOT/'reports/performance-followup-1555742041789440011-24h-evidence'; OUT.mkdir(exist_ok=True)
START=datetime.datetime.fromisoformat('2026-10-02T18:50:43-04:00'); NOW=datetime.datetime.now(ET)
def save(name,data):
 (OUT/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
def run(args):
 p=subprocess.run(args,capture_output=True,text=True); assert p.returncode==0,(args[0],p.returncode,p.stderr[:200]); return p.stdout
status=json.loads(run(['python3',str(ROOT/'scripts/mgs-performance-status.py')])); save('host-observation.json',status)
names=['dtr-sb-page-health-sync','sync-sb-sms-revenue-daily','sync-sb-messenger-revenue-sheet','monitor-sb-messenger-token-invalid']
dec=json.JSONDecoder(); logs={}
def objects(lines):
 s='\n'.join(l for l in lines if not l.startswith('BROWSER_BUDGET ')); objs=[];pos=0
 while pos<len(s):
  k=s.find('{',pos)
  if k<0:break
  try:o,end=dec.raw_decode(s,k);pos=end
  except json.JSONDecodeError:pos=k+1;continue
  if isinstance(o,dict):objs.append(o)
 return objs
safe_keys={'status','ok','mode','started_at_et','completed_at_et','period_start','period_end','target_date','groups','source_rows','publishers','api_rows','named_sheet_rows','matched_rows','updated_cells','readback','readback_ok','errors','scanned_users','active_users','sb_rows','restricted_pages','patches','applied','dry_run','sheet','sheet_id','spreadsheet_id','range','backup','alerts_seen','new_alerts','refreshed_incidents','daily','last_seen_id','state','warnings','report_path','destination','sheet_sync','summary'}
def safe(o):
 if isinstance(o,dict):return {k:safe(v) for k,v in o.items() if k in safe_keys or k in {'date','active','resolved','rollover','daily_sent','total','verified','expected','actual','changed','readback_rows','sheet_range'}}
 if isinstance(o,list):return [safe(v) for v in o if isinstance(v,(dict,int,float,bool))][:20]
 return o
for n in names:
 lines=(ROOT/'logs'/f'{n}.log').read_text().splitlines(); events=[];errors=[]
 for i,l in enumerate(lines):
  if 'BROWSER_BUDGET ' in l:
   try: events.append({'line':i+1,**json.loads(l.split('BROWSER_BUDGET ',1)[1])})
   except ValueError:errors.append({'line':i+1,'type':'invalid_lifecycle_json'})
 releases=[e for e in events if e.get('event')=='released'];waits=[e['wait_seconds'] for e in events if 'wait_seconds' in e];dur=[e['run_seconds'] for e in releases if 'run_seconds' in e]
 obs=objects(lines); latest=obs[-1] if obs else {}; markers=[{'line':i+1,'at':m.group(1),'kind':m.group(2),'rc':m.group(3)} for i,l in enumerate(lines) if (m:=re.search(r'^\[([^]]+)\].*\b(START|END).*?(?:rc=(\d+))?$',l))]
 logs[n]={'file_lines':len(lines),'lifecycle_records':len(events),'event_counts':dict(Counter(e.get('event') for e in events)),'outcomes':dict(Counter(e.get('outcome') for e in releases)),'wait_max_seconds':max(waits) if waits else None,'wait_nonzero_count':sum(w>0 for w in waits),'duration_seconds':{'min':min(dur),'median':statistics.median(dur),'max':max(dur),'sum':sum(dur)} if dur else {},'events':events,'parse_errors':errors,'object_count':len(obs),'latest_keys':list(latest),'latest_safe':safe(latest),'last_objects_safe':[safe(o) for o in obs[-4:]],'timestamp_markers':markers[-8:],'error_line_counts':dict(Counter(key for l in lines[events[0]['line']-1:] for key in ['Traceback (most recent call last)','BROWSER_BUDGET_ERROR','admission_timeout','"outcome":"error"'] if key in l)) if events else {},'lifecycle_individual_timestamps':False}
 save('monitor-observation-summary.json' if n=='monitor-sb-messenger-token-invalid' else f'{n}-summary.json',logs[n])
j=json.loads('[]');ledger=[]
for l in run(['journalctl','-u','cron','--since','2026-10-02 18:50:43','--no-pager','-o','json']).splitlines():
 o=json.loads(l);m=o.get('MESSAGE','');matches=[n for n in names if n in m]
 if matches and 'CMD (' in m and '--cleanup-old-messages' not in m:
  ledger.append({'at':datetime.datetime.fromtimestamp(int(o['__REALTIME_TIMESTAMP'])/1e6,ET).isoformat(),'consumer':matches[0],'apply_argument':'--apply' in m,'entrypoint_script':re.findall(r'/root/mgs-agent/scripts/[\w.-]+',m),'business_command_redacted':True})
save('natural-dispatches.json',{'since':START.isoformat(),'until':NOW.isoformat(),'counts':dict(Counter(x['consumer'] for x in ledger)),'dispatches':ledger})
cpu=[];meta=[]
for day in ['02','03']:
 d=json.loads(run(['sadf','-j',f'/var/log/sysstat/sa{day}','--','-u']));h=d['sysstat']['hosts'][0];meta.append({k:v for k,v in h.items() if k!='statistics'})
 for o in h.get('statistics',[]):
  t=o['timestamp']; at=datetime.datetime.fromisoformat(t['date']+'T'+t['time']).replace(tzinfo=datetime.timezone.utc if t.get('utc') else ET).astimezone(ET)
  for c in o.get('cpu-load',[]):
   if c.get('cpu')=='all':cpu.append({'at':at.isoformat(),'interval_seconds':t.get('interval'),'busy_pct':round(100-c['idle'],2),'iowait_pct':c['iowait'],'steal_pct':c['steal']})
def stats(rows):
 return {'count':len(rows),'first':rows[0]['at'] if rows else None,'last':rows[-1]['at'] if rows else None,'weighted_interval_busy_pct':round(sum(r['busy_pct']*r['interval_seconds'] for r in rows)/sum(r['interval_seconds'] for r in rows),3) if rows else None,'max_interval_mean_busy_pct':max(r['busy_pct'] for r in rows) if rows else None}
period=[r for r in cpu if START<datetime.datetime.fromisoformat(r['at'])<=NOW]
compare={day:stats([r for r in cpu if datetime.datetime.fromisoformat(r['at']).strftime('%Y-%m-%d')==day and '07:00'<=datetime.datetime.fromisoformat(r['at']).strftime('%H:%M')<='16:00']) for day in ['2026-10-02','2026-10-03']}
save('sysstat-intervals.json',{'metadata':meta,'samples':cpu,'post_rollout':stats(period),'equivalent_clock_windows_0700_1600_ET':compare,'causal_gain_validated':False})
summary={'observed_at':NOW.isoformat(),'elapsed_hours':(NOW-START).total_seconds()/3600,'host':status,'logs':{n:{k:v for k,v in o.items() if k not in {'events','timestamp_markers','last_objects_safe'}} for n,o in logs.items()},'dispatch_counts':dict(Counter(x['consumer'] for x in ledger)),'business_dispatches':[x for x in ledger if 'token-invalid' not in x['consumer']],'sysstat_post_rollout':stats(period),'equivalent_windows':compare,'restarts':[x.get('restarts') for x in meta]}
save('collection-summary.json',summary)
print(json.dumps({**summary,'host':{k:v for k,v in status.items() if k not in {'profiles','browser_budget'}},'logs':{n:{k:v for k,v in o.items() if k not in {'latest_keys','latest_safe','object_count','file_lines'}} for n,o in summary['logs'].items()}},ensure_ascii=False,indent=2))
