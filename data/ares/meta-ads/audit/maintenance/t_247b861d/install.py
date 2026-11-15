#!/usr/bin/env python3
"""Install staged cutover by CAS; suspend ONLY historical coordination."""
import fcntl,hashlib,importlib.util,json,os,sys
from contextlib import ExitStack
from datetime import datetime,timezone
from pathlib import Path
R=Path('/root/mgs-agent');H=Path(__file__).parent;A='1034081997659047';OLD='eggbev-pg23187-1570285402068091011';NEW='eggbev-pg23189-1571342489162489937'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
def atomic(p,raw,mode=0o600):
 p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_name(p.name+'.t_247b861d.new');tmp.write_bytes(raw);tmp.chmod(mode);os.replace(tmp,p)
def main():
 changes=json.loads((H/'changes.json').read_text());testpath='tests/test_eggbev_ana_integration.py';test=H/'isolated'/testpath
 changes[testpath]={'before_sha256':None,'after_sha256':sha(test)}
 dest=H/'staged'/testpath;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(test.read_bytes())
 (H/'changes.json').write_text(json.dumps(changes,indent=2)+'\n')
 cfg=json.loads((R/'data/ares/meta-ads/engine-v3/config.json').read_text());root=Path(cfg['state_root'])
 # Existing shared maintenance and operation locks; request locks protect both source runs.
 locks=[R/'scripts/ares_campaign_v3/.maintenance.lock',R/'data/ares/meta-ads/state/Eggbev-US-CC-EN-BOT/roas-cycle.lock']
 home=R/'data/ares/meta-ads/audit/eggbev/target-clone'
 locks += [home/OLD/'target-clone.lock',home/OLD/'execution-now-1570313437379170436/target-clone.lock',home/NEW/'target-clone.lock']
 # No active campaign/guard process may straddle cutover. Store counts, never argv/secrets.
 active=[]
 for p in Path('/proc').glob('[0-9]*/cmdline'):
  try:
   args=p.read_bytes().split(b'\0')
   if any(arg.decode(errors='replace').startswith(str(R/'scripts/ares-eggbev')) for arg in args):active.append(p.parent.name)
  except OSError:pass
 assert not active,'active Eggbev consumer: stop installation, reconcile real owner'
 with ExitStack() as stack:
  for path in locks:
   path.parent.mkdir(parents=True,exist_ok=True);h=stack.enter_context(path.open('a+'));fcntl.flock(h,fcntl.LOCK_EX|fcntl.LOCK_NB)
  for filename,record in changes.items():
   assert sha(R/filename)==record['before_sha256'],f'CAS drift: {filename}'
   assert sha(H/'staged'/filename)==record['after_sha256'],f'staged drift: {filename}'
  lp=root/'writer-leases'/f'{A}.json';lease=json.loads(lp.read_text());assert lease['request_id']==OLD and lease['status']=='RECOVERY_PENDING' and lease['blocks_readers'] is True
  lease_sha=sha(lp);(H/'lease-before.json').write_bytes(lp.read_bytes())
  pins={}
  for p in [root/'checkpoints'/f'{OLD}-{A}.json',root/'target-continuations'/f'{OLD}-{A}.json']:
   pins[str(p.relative_to(root))]=sha(p);backup=H/'historical-backup'/p.name;backup.parent.mkdir(parents=True,exist_ok=True);backup.write_bytes(p.read_bytes())
  # Pin a sanitized observation inside state; raw historical journals remain untouched.
  observation=root/'operator-suspensions'/f'{OLD}-{A}-observation.json'
  raw=(H/'pre-cutover-readback.json').read_bytes();assert not observation.exists();atomic(observation,raw);pins[str(observation.relative_to(root))]=sha(observation)
  receipt={'schema_version':1,'account_id':A,'request_id':OLD,'status':'SUSPENDED_BY_OPERATOR','authority_message_ids':['1570338387380936737','1570343663307989043'],'campaign_qa_complete':False,'meta_writes':0,'reservation_release':False,'recorded_at':datetime.now(timezone.utc).isoformat(),'record_pins':pins,'previous_lease_sha256':lease_sha,'campaign_ids_preserved':['120251175890330629'],'historical_uncertainties':'Historical failure and partial journals remain unchanged. Human modified campaign after API partial effects; no QA COMPLETE or causal claim. No automatic recovery permitted.','observation_evidence':'data/ares/meta-ads/audit/maintenance/t_247b861d/pre-cutover-readback.json'}
  rp=root/'operator-suspensions'/f'{OLD}-{A}.json';assert not rp.exists();atomic(rp,(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n').encode())
  # New module first, consumers then data. Existing blocking lease remains throughout.
  order=sorted(changes,key=lambda p:(0 if p.endswith('operator_suspension.py') else 1 if p.startswith('scripts/') else 2,p))
  installed=[]
  for filename in order:
   target=R/filename;assert sha(target)==changes[filename]['before_sha256'],f'CAS changed during install: {filename}'
   mode=target.stat().st_mode&0o777 if target.exists() else 0o644
   atomic(target,(H/'staged'/filename).read_bytes(),mode);installed.append(filename)
  sys.path.insert(0,str(R/'scripts'))
  from ares_campaign_v3.coordination import AccountWriterLeaseStore,reader_block_reason
  from ares_campaign_v3.operator_suspension import deny_replay
  result=AccountWriterLeaseStore(root).suspend_operator(A,OLD,expected_sha256=lease_sha)
  assert result['status']=='SUSPENDED_BY_OPERATOR' and result['campaign_qa_complete'] is False
  assert reader_block_reason(A,root) is None
  try:deny_replay(root,A,OLD)
  except ValueError:pass
  else:raise AssertionError('historical replay fence missing')
  for filename in changes:assert sha(R/filename)==changes[filename]['after_sha256']
  after=json.loads((R/'data/ares/meta-ads/engine-v3/config.json').read_text());after['accounts'].pop(A)
  before=json.loads((H/'other-account-config-before.json').read_text());assert after==before,'other accounts or global config mutated'
  result={'installed':installed,'file_count':len(installed),'cas_all_passed':True,'other_accounts_and_global_config_unchanged':True,'lease':result,'suspension_receipt':str(rp.relative_to(R)),'suspension_receipt_sha256':sha(rp),'reader_gate':None,'historical_replay_blocked':True,'meta_writes':0,'campaign_preparation':False,'active_consumer_count':0,'at':datetime.now(timezone.utc).isoformat()}
  atomic(H/'install-receipt.json',(json.dumps(result,indent=2)+'\n').encode());print(json.dumps({'installed_files':len(installed),'cas_passed':True,'other_accounts_unchanged':True,'lease_status':result['lease']['status'],'reader_gate':None,'meta_writes':0}))
if __name__=='__main__':main()
