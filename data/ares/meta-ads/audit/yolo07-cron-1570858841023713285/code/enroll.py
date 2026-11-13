"""Promote one approved read-only report route; preserve every existing binding."""
from pathlib import Path
import json,copy,os,fcntl,datetime,difflib,hashlib,sys
BASE=Path('/root/mgs-agent');ROOT=BASE/'data/ares/meta-ads/audit/yolo07-cron-1570858841023713285'
AID='1492168699397108';TID='1569767319339663361';NAME='Yolokfx-US-SHEIN-EN-07-G002';MODE=sys.argv[1]
def load(p):return json.loads(Path(p).read_text())
def save(p,obj):
 p=Path(p);tmp=p.with_name(p.name+'.tmp');tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n');tmp.chmod(0o600);os.replace(tmp,p)
def commit(p,before,after):
 assert load(p)==before,'Concurrent canonical edit'
 diff=''.join(difflib.unified_diff(json.dumps(before,ensure_ascii=False,indent=2).splitlines(True),json.dumps(after,ensure_ascii=False,indent=2).splitlines(True)))
 (ROOT/(p.name+'.diff')).write_text(diff);save(p,after)
assert load(ROOT/'permission-journal.json')['status']=='VERIFIED'
pre=load(ROOT/'live-preflight.json');acc=next(x['identity'] for x in pre if x['label']=='target' and x['http']==200);assert acc['id'].removeprefix('act_')==AID and acc['name']==NAME and acc['currency']=='USD' and acc['timezone_name']=='America/New_York'
if MODE=='prepare':
 now=datetime.datetime.now(datetime.timezone.utc).isoformat();binding={'thread_id':TID,'channel_id':'1558146629805023424','thread_name':'📈Yolokfx Conta 07 Intraday','manager_code':'g002','account_id':AID,'account_name':NAME,'mode':'on_demand_read_only','layout_source':'data/ares/meta-ads/operations/SHEIN-US-DIRECT.json#/reporting/on_demand_default_layout','renderer':'/root/.hermes/profiles/ares/scripts/shein-report-layout.py','require_render_and_validate_before_delivery':True,'historical_messages_not_default_model':True,'reporting_enrolled_at':now,'source_message_id':'1570858841023713285','permission_approval_message_id':'1570860329947103396'}
 p=BASE/'data/ares/meta-ads/operations/SHEIN-US-DIRECT-accounts.json';before=load(p);after=copy.deepcopy(before)
 if not any(x['account_id']==AID for x in after['accounts']):
  new={'account_id':AID,'name':NAME,'manager_code':'G002','manager_name':'Geizian','manager_discord_id':'321263240782807040','channel_id':'1548149300826079333','channel_name':'shein-g002','currency':acc['currency'],'timezone_name':acc['timezone_name'],'account_status':acc['account_status'],'relationship':'owned','engine_registered':False,'registered_modes':[],'single_clone_runtime_enabled':False,'account_prerequisite_status':'REPORT_READ_ONLY_VALIDATED','reporting_enrolled_at':now,'reporting_source_message_id':'1570858841023713285'}
  after['accounts'].append(new);after['account_count']=len(after['accounts']);after['counts_by_manager']['G002']+=1;after['last_scoped_reconciliation']={'account_id':AID,'source_message_id':'1570858841023713285','observed_at':now,'source':'exact allowed account GET;no portfolio discovery'}
  assert after['accounts'][:-1]==before['accounts'];commit(p,before,after)
 p=BASE/'data/ares/discord/shein-intraday-report-bindings.json';before=load(p);after=copy.deepcopy(before)
 if not any(x['account_id']==AID for x in after['bindings']):
  after['bindings'].append(binding);after['pending_bindings']=[x for x in after.get('pending_bindings',[]) if x['account_id']!=AID];after['binding_count']=len(after['bindings']);after['scope']='SHEIN six manager report channels; canonical active account Intraday threads'
  assert after['bindings'][:-1]==before['bindings'];commit(p,before,after)
 else:binding=next(x for x in after['bindings'] if x['account_id']==AID);now=binding['reporting_enrolled_at']
 p=BASE/'data/ares/meta-ads/operations/SHEIN-US-DIRECT.json';before=load(p);after=copy.deepcopy(before);cfg=after['reporting']['on_demand_default_layout'];ref='787796726891306';refname='Yolokfx-US-SHEIN-EN-05-G001';refthread='1558146488599842827'
 def transform(v):
  if isinstance(v,dict):return {k:transform(x) for k,x in v.items()}
  if isinstance(v,list):return [transform(x) for x in v]
  if isinstance(v,str):return {ref:AID,refname:NAME,refthread:TID}.get(v,v)
  return v
 for key in ['account_report_overrides','account_budget_display_overrides']:
  if AID not in cfg[key]:
   entry=transform(copy.deepcopy(cfg[key][ref]));entry.update(account_name=NAME,extension_authority_message_id='1570858841023713285',permission_approval_message_id='1570860329947103396',effective_from_financial_snapshot=cfg[key][ref]['effective_from_financial_snapshot'],reporting_enrolled_at=now,scope='explicit_Yolokfx07_G002_reporting_extension')
   if key=='account_report_overrides':entry['manager_code']='g002';entry['thread_id']=TID
   cfg[key][AID]=entry
  cfg[key][AID]['effective_from_financial_snapshot']=cfg[key][ref]['effective_from_financial_snapshot']
  cfg[key][AID]['reporting_enrolled_at']=now
 profile=cfg['account_report_overrides'][AID]['options']['format_profile_id'];ids=cfg['format_profiles'][profile]['account_ids']
 if AID not in ids:ids.append(AID)
 for key in ['budget_used_standard','compact_identity_standard']:
  obj=cfg[key]
  if AID not in obj['account_ids']:obj['account_ids'].append(AID)
  if 'thread_ids' in obj and TID not in obj['thread_ids']:obj['thread_ids'].append(TID)
  if 'account_bindings' in obj and AID not in obj['account_bindings']:obj['account_bindings'][AID]=transform(copy.deepcopy(obj['account_bindings'][ref]))
  if 'account_bindings' in obj and isinstance(obj['account_bindings'].get(AID),dict):obj['account_bindings'][AID]['manager_code']='g002'
 assert all(after[k]==before[k] for k in before if k!='reporting');commit(p,before,after)
 save(ROOT/'report-binding.json',binding);print(json.dumps({'status':'CATALOG_BINDING_LAYOUT_PREPARED','active_bindings':len(load(BASE/'data/ares/discord/shein-intraday-report-bindings.json')['bindings']),'cron_membership':'unchanged until target smoke passes'}))
elif MODE=='policies':
 smoke=load(ROOT/'smoke-result.json');assert smoke['status'] in ('TARGET_LIVE_INTRADAY_RENDER_VALIDATED_NO_POST','TARGET_LIVE_D1_INTRADAY_RENDER_VALIDATED_NO_POST') and smoke['account_id']==AID
 policy_paths=[BASE/'data/ares/meta-ads/policies'/n for n in ['shein-daily-report.json','shein-intraday-report.json']]
 lock=Path('/root/mgs-agent/data/ares/meta-ads/state/shein-daily-report/run.lock')
 with lock.open('a+') as fh:
  fcntl.flock(fh,fcntl.LOCK_EX|fcntl.LOCK_NB)
  for p in policy_paths:
   before=load(p);after=copy.deepcopy(before)
   if AID not in after['account_ids']:after['account_ids'].append(AID);after['thread_ids'].append(TID)
   after['expected_reports']=len(after['account_ids']);after.pop('expected_reports_per_manager',None)
   index=load(BASE/'data/ares/discord/shein-intraday-report-bindings.json')['bindings'];chosen=[b for b in index if b['account_id'] in set(after['account_ids'])]
   assert len(chosen)==len(after['account_ids']);after['expected_reports_by_manager']={f'g00{i}':sum(str(b['manager_code']).casefold()==f'g00{i}' for b in chosen) for i in range(1,7)}
   after['membership_extensions']={**after.get('membership_extensions',{}),AID:{'thread_id':TID,'manager_code':'g002','authorized_by_discord_id':'344196393512075265','source_message_id':'1570858841023713285','permission_approval_message_id':'1570860329947103396','evidence':'data/ares/meta-ads/audit/yolo07-cron-1570858841023713285/smoke-result.json'}}
   assert set(after['account_ids'])-set(before['account_ids'])<={AID};assert set(after['thread_ids'])-set(before['thread_ids'])<={TID}
   assert after['enabled']==before['enabled'];commit(p,before,after)
 print('EXACT_TARGET_ADDED_TO_BOTH_EXISTING_POLICIES;COUNTS_DERIVED_FROM_EACH_POLICY;NO_NEW_CRON')
else:raise ValueError(MODE)
