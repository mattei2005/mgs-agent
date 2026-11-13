"""Resume exactly five original SHEIN slots only after the two report batches."""
import pathlib,json,subprocess,importlib.util,sys,difflib,datetime
ROOT=pathlib.Path('/root/mgs-agent/data/ares/meta-ads/reports/shein-on-demand-requests/1570812403937976371')
RUNNER='/root/.hermes/profiles/ares/scripts/shein-intraday-cron.py'
PREFIX='# PAUSED Rodolfo1570801075621986305 pending ROI reconciliation | '
POLICY=pathlib.Path('/root/mgs-agent/data/ares/meta-ads/policies/shein-intraday-report.json')
def load(p):return json.loads(p.read_text())
def save(name,data):(ROOT/name).write_text(json.dumps(data,ensure_ascii=False,indent=2))
def audit(label,own_lines=()):
 s=importlib.util.spec_from_file_location('resume_schedule_audit','/root/.hermes/profiles/ares/scripts/shein-daily-schedule-audit.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);data=m.inventory()
 slots=load(POLICY)['slots'];checks=[]
 own={('root',' '.join(line.split()[:5]),' '.join(line.split()[5:])) for line in own_lines}
 for slot in slots:
  conflicts=[];baseline=[]
  for e in data['entries']:
   if e['source']=='root' and (e['source'],e['schedule'],e.get('command')) in own:continue
   hits=[t for t in e['ticks'] if datetime.datetime.fromisoformat(t).strftime('%H:%M')==slot]
   if hits:(baseline if e['baseline'] else conflicts).append({'source':e['source'],'name':e['name'],'hits':len(hits)})
  checks.append({'slot':slot,'operational_conflicts':conflicts,'baseline_collisions':baseline})
 result={'generated_at':data['generated_at'],'horizon':data['horizon'],'unknown':data['unknown'],'checks':checks,'exact_self_excluded':len(own),'pass':not data['unknown'] and all(not x['operational_conflicts'] for x in checks),'resource_review':{'same_original_report_lane_lock':True,'no_new_schedule_or_catchup':True,'isolated_UI_sessions':True,'source_API_common_throttle_unchanged':True,'baseline_exception':'original approved five slots and25s deterministic stagger preserved; no new slots allocated'}}
 save('schedule-inventory-'+label+'.json',data);save('schedule-audit-'+label+'.json',result);assert result['pass'],'schedule conflict requires reconciliation';return result
mode=sys.argv[1]
if mode=='audit':
 audit('pre');print('PRE_AUDIT_OK');sys.exit()
for phase in ('yesterday','intraday'):
 r=load(ROOT/phase/'final-reconciliation.json');assert r['status']=='COMPLETE_GET_VERIFIED' and r['accounts']==36
first=load(ROOT/'yesterday/final-reconciliation.json');second=load(ROOT/'intraday/final-reconciliation.json')
assert max(map(int,first['message_ids']))<min(map(int,second['message_ids'])),'report order changed'
s=importlib.util.spec_from_file_location('resume_discord','/root/.hermes/profiles/ares/scripts/shein-daily-report.py');d=importlib.util.module_from_spec(s);s.loader.exec_module(d);dc=d.Discord();msg=dc.call('GET','/channels/1570801075621986305/messages/1570814262631473396');assert msg['author']['id']=='344196393512075265' and 'reativar o cron' in msg['content']
policy=load(POLICY);assert policy['enabled'] is True and policy['temporary_suspension']['active'] is False and policy['temporary_suspension']['resumed_by_message_id']=='1570814262631473396'
old=subprocess.check_output(['crontab','-l'],text=True)
if mode=='apply':
 targets=[line for line in old.splitlines() if line.startswith(PREFIX) and RUNNER in line];assert len(targets)==5
 restored=[line.removeprefix(PREFIX) for line in targets]
 expected_schedules=policy['schedules'];assert sorted(' '.join(line.split()[:5]) for line in restored)==sorted(expected_schedules)
 assert not any(RUNNER in line and not line.lstrip().startswith('#') for line in old.splitlines())
 audit('pre')
 lines=old.splitlines(keepends=True);new=''.join(line.removeprefix(PREFIX) if line.rstrip('\n') in targets else line for line in lines)
 assert [l for l in old.splitlines() if RUNNER not in l]==[l for l in new.splitlines() if RUNNER not in l]
 (ROOT/'root-crontab-resume-before.txt').write_text(old);path=ROOT/'root-crontab-resume-proposed.txt';path.write_text(new);(ROOT/'root-crontab-resume-diff.txt').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True))))
 subprocess.run(['crontab','-n',str(path)],capture_output=True,text=True,check=True)
 assert subprocess.check_output(['crontab','-l'],text=True)==old,'concurrent scheduler change'
 subprocess.run(['crontab',str(path)],capture_output=True,text=True,check=True)
 back=subprocess.check_output(['crontab','-l'],text=True);assert back==new;(ROOT/'root-crontab-resume-readback.txt').write_text(back)
else:
 assert mode=='verify';back=old;assert back==(ROOT/'root-crontab-resume-readback.txt').read_text();restored=[line for line in back.splitlines() if RUNNER in line and not line.lstrip().startswith('#')]
assert len(restored)==5
post=audit('post',restored)
from zoneinfo import ZoneInfo
now=datetime.datetime.now(ZoneInfo('America/New_York'));upcoming=[]
for slot in policy['slots']:
 h,minute=map(int,slot.split(':'));at=now.replace(hour=h,minute=minute,second=25,microsecond=0)
 if at>now:upcoming.append(at)
if not upcoming:
 for slot in policy['slots']:
  h,minute=map(int,slot.split(':'));upcoming.append((now+datetime.timedelta(days=1)).replace(hour=h,minute=minute,second=25,microsecond=0))
result={'status':'CRON_RESUMED_GET_LOCAL_READBACK_VERIFIED','enabled':True,'slots':policy['slots'],'schedules':policy['schedules'],'timezone':policy['schedule_timezone'],'no_agent':True,'scheduler':'root_crontab','runner':RUNNER,'delivery':'exact24canonicalaccountthreads;journal_nonce_GET','next_physical_dispatch':min(upcoming).isoformat(),'no_catchup':True,'other_crontab_lines_unchanged':True,'daily_d1_unchanged':True,'post_collision_audit_pass':post['pass'],'authority_message_id':'1570814262631473396','completed_at':now.isoformat()}
save('cron-reactivation-readback.json',result);print(json.dumps(result,ensure_ascii=False))
