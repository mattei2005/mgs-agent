import json,re,datetime,statistics,subprocess,importlib.util,os
from pathlib import Path
from collections import Counter
from zoneinfo import ZoneInfo
ROOT=Path('/root/mgs-agent');OUT=ROOT/'reports/performance-followup-1555742041789440011-24h-evidence';ET=ZoneInfo('America/New_York');dec=json.JSONDecoder()
def save(n,d):(OUT/n).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def objs(lines):
 s='\n'.join(l for l in lines if 'BROWSER_BUDGET ' not in l); pos=0;out=[]
 while pos<len(s):
  k=s.find('{',pos)
  if k<0:break
  try:o,end=dec.raw_decode(s,k);pos=end
  except ValueError:pos=k+1;continue
  if isinstance(o,dict):out.append(o)
 return out
results=[]
lines=(ROOT/'logs/dtr-sb-page-health-sync.log').read_text().splitlines();starts=[i for i,l in enumerate(lines) if re.match(r'^\[2026-10-03T(?:07:30|15:30):',l) and ' START ' in l]
for i in starts:
 end=next(j for j in range(i+1,len(lines)) if ' END rc=' in lines[j]);block=lines[i:end+1];o=objs(block)[-1];ev=[json.loads(l.split('BROWSER_BUDGET ',1)[1]) for l in block if 'BROWSER_BUDGET ' in l]
 sheet=o.get('sheet_update',{});readback_ok=sheet.get('readback_ok');errors=o.get('errors',[])
 # Preserve counters and safe metadata only; exclude per-page/user payloads.
 summary={k:v for k,v in o.items() if k in ['ok','mode','sheet_active_users','matched_1p_users','sb_rows','sb_active_restricted_start','stats','writes','backup_rows','new_restrictions_alerted','started_at','finished_at','sheet','log','restricted_sheet_rows','restricted_users','expired_restrictions']}
 sheet_safe={k:v for k,v in sheet.items() if isinstance(v,(int,float,bool)) or (isinstance(v,str) and (k in ['sheet','spreadsheet_id','range','status','mode','url']))}
 results.append({'consumer':'dtr','wrapper_start':re.match(r'^\[([^]]+)\]',block[0]).group(1),'wrapper_end':re.match(r'^\[([^]]+)\]',block[-1]).group(1),'wrapper_rc':int(re.search(r'rc=(\d+)',block[-1]).group(1)),'lifecycle_events':ev,'summary':summary,'sheet_keys':list(sheet),'sheet_readback':sheet_safe,'errors_count':len(errors),'errors_types':[list(e) if isinstance(e,dict) else type(e).__name__ for e in errors],'pass':o.get('ok') is True and o.get('mode')=='apply' and not errors and readback_ok is True and any(e.get('event')=='released' and e.get('outcome')=='success' for e in ev)})
sms=objs((ROOT/'logs/sync-sb-sms-revenue-daily.log').read_text().splitlines())[-1]
sms_rb=sms.get('readback',{});results.append({'consumer':'sms','target_date':sms.get('target_date'),'status':sms.get('status'),'groups':sms.get('groups'),'source_rows':sms.get('source_rows'),'readback_status':sms_rb.get('status'),'readback_counts_equal':all(sms_rb.get(k)==sms.get(k) for k in ['groups','source_rows','revenue_cents','net_revenue_cents','investment_cents']),'destination':'RunCloud Inc02 /home/runcloud2/webapps/creditoparaveiculo / mgs-quiz-carro daily revenue','pass':sms.get('status')=='SYNC_OK' and sms_rb.get('status')=='DAILY_REVENUE_IMPORT_OK'})
msg=json.load(open(ROOT/'data/sb-messenger-revenue-sheet-sync-state.json'));results.append({'consumer':'messenger','status':msg.get('status'),'started_at_et':msg.get('started_at_et'),'completed_at_et':msg.get('completed_at_et'),'publishers':msg.get('publishers'),'matched_rows':msg.get('matched_rows'),'readback':msg.get('readback'),'sheet_id':msg.get('sheet_id'),'destination_keys':{k:v for k,v in msg.items() if k in ['sheet_name','sheet_tab','sheet_title','sheet_named_rows','sheet_gid','column']},'state_equals_log':msg==objs((ROOT/'logs/sync-sb-messenger-revenue-sheet.log').read_text().splitlines())[-1],'pass':msg.get('status')=='SYNC_OK' and msg.get('readback')=='exact_cents_ok'})
t=json.load(open(ROOT/'data/sb-messenger-token-invalid-monitor.json'));ledger=json.load(open(OUT/'natural-dispatches.json'));mon=json.load(open(OUT/'monitor-observation-summary.json'));results.append({'consumer':'invalid_messenger_monitor','natural_regular_dispatches':ledger['counts']['monitor-sb-messenger-token-invalid'],'all_log_successful_releases':mon['outcomes'].get('success',0),'prevalidation_in_log':1,'excluded_auxiliary_cleanup_mode':True,'last_check':t.get('last_check'),'last_seen_id':t.get('last_seen_id'),'consecutive_failures':t.get('consecutive_failures'),'pending_present':t.get('pending') is not None,'last_error_present':t.get('last_error') is not None,'retained_incidents_count':len(t.get('incidents',{})),'historical_incidents_not_current_notifications':True,'latest_live_result':mon['latest_safe'],'pass':t.get('consecutive_failures')==0 and not t.get('last_error') and not t.get('pending') and mon['outcomes'].get('success',0)==ledger['counts']['monitor-sb-messenger-token-invalid']+1})
save('observable-cycle-validation.json',{'results':results,'all_pass':all(r['pass'] for r in results),'verification_basis':'natural log results, cron dispatches, consumer internal readbacks, local persisted Messenger/monitor state; no new remote business writes or benchmark reruns'})
s=json.load(open(OUT/'sysstat-intervals.json'));maps={day:{datetime.datetime.fromisoformat(r['at']).strftime('%H:%M'):r for r in s['samples'] if r['at'].startswith(day) and '07:10'<=datetime.datetime.fromisoformat(r['at']).strftime('%H:%M')<='16:00' and 595<=r['interval_seconds']<=605} for day in ['2026-10-02','2026-10-03']};common=sorted(set(maps['2026-10-02'])&set(maps['2026-10-03']));pair={'matched_clock_interval_end_times':common,'interval_start_end_contract':'matched ~600-second intervals ending 07:10..16:00 ET; reboot-gap slots excluded from both days','sample_pairs':len(common),'weighted_cpu_busy_pct':{day:round(sum(maps[day][k]['busy_pct']*maps[day][k]['interval_seconds'] for k in common)/sum(maps[day][k]['interval_seconds'] for k in common),3) for day in maps},'maximum_interval_mean_busy_pct':{day:max(maps[day][k]['busy_pct'] for k in common) for day in maps},'causal_gain_proven':False,'confounders':['authorized Hermes staging/test workloads and finance QA','reboots and cold/hot cache differences','business inputs differ by date','no controlled workload or same frozen request set']}
save('equivalent-interval-comparison.json',pair)
print(json.dumps({'cycles':results,'comparison':pair},ensure_ascii=False,indent=2))
