"""Live SA acceptance of installed canonical consumer. No Drive/Meta writes."""
from pathlib import Path
import concurrent.futures,hashlib,importlib.util,json,sys,contextlib,fcntl
ROOT=Path('/root/mgs-agent');sys.path.insert(0,str(ROOT/'scripts'))
import ares_archive_storage as storage
import ares_archive_readonly_reconciliation as reconciliation
H=storage.b.DATA/'consumer-recovery-t_1b4f5263'
baseline=storage.b.read_json(H/'baseline.json');installation=storage.b.read_json(H/'installation-receipt.json')
spec=importlib.util.spec_from_file_location('consumer_accepted_shein',ROOT/'scripts/ares-shein-campaigns.py');assert spec and spec.loader
ops=importlib.util.module_from_spec(spec);spec.loader.exec_module(ops)
drive=storage.drive();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
# Serialize the read-only acceptance window against legitimate external writers.
locks=contextlib.ExitStack();locks.enter_context(storage.b.queue_lock())
inv=ROOT/'data/ares/creative-ops/inventory/assets.jsonl'
lock=locks.enter_context(inv.with_suffix(inv.suffix+'.lock').open('a+'));fcntl.flock(lock,fcntl.LOCK_EX)
verification_inventory_sha=sha(inv)
(H/'inventory-at-acceptance.jsonl').write_bytes(inv.read_bytes())
def check(row):
 fid=row['asset_drive_id']
 try:
  result=ops.drive_file_readback(drive.token,fid)
  assert result['id']==fid and result['name']==row['canonical_filename']
  assert result['sha256Checksum']==row['clean_checksum']
  assert result['parents']==['1bYwFC_jIK4-JMSmkWfUKFWkoHRL_udwX']
  return {'logical_id':fid,'name':result['name'],'passed':True,'provider_id':result['provider_id'],'stock_id':result['stock_file_id'],'sha256':result['sha256Checksum'],'parents':result['parents']}
 except Exception as exc:return {'logical_id':fid,'passed':False,'exception':type(exc).__name__,'reason':str(exc)}
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(check,baseline['inventory_rows']))
assert len(results)==34 and len({x['logical_id'] for x in results})==34
failed=[x for x in results if not x['passed']]
protected={p:sha(ROOT/p) for p in baseline['file_sha256'] if p not in installation['after']}
assert all(value==baseline['file_sha256'][p] for p,value in protected.items()),'protected_file_changed'
assert all(sha(ROOT/p)==value for p,value in installation['after'].items()),'installation_digest_changed'
assert sha(inv)==verification_inventory_sha,'whole_inventory_changed_during_locked_acceptance'
rows=[json.loads(x) for x in inv.read_text().splitlines() if x.strip()]
for expected in baseline['inventory_rows']:assert [r for r in rows if r['asset_id']==expected['asset_id']]==[expected]
proof=storage.b.read_json(H/'approved-native-proof.json');native=[]
for rec in proof['records']:
 e=storage.mapping(rec['frozen_entry']['sourceId']);assert e==rec['frozen_entry']
 assert storage.namespace.override(e) is None
 assert storage.require_historical_ack(drive,e)
 for kind,fid in [('provider',e['archiveId']),('source',e['sourceId'])]:
  live=storage.meta(drive,fid);before=rec[kind]
  for field in ['id','name','mimeType','size','md5Checksum','sha256Checksum','parents','owners','trashed','version']:
   assert live.get(field)==before.get(field),(fid,field)
 assert storage.download_id(e['sourceId'],drive.token)==e['archiveId']
 native.append({'logical_id':e['sourceId'],'frozen_mapping_unchanged':True,'source_and_provider_metadata_unchanged':True,'ack_unchanged_and_valid':True,'download_provider_id':e['archiveId']})
intake=ROOT/'data/ares/meta-ads/audit/shein/campaigns/intake/shein-1569454008337301577'
phases={f:(intake/f).exists() for f in ['media-preparation.json','request-ready.json']}
phases['campaign_state_exists']=(ROOT/'data/ares/meta-ads/state/shein/campaigns/shein-1569454008337301577.json').exists()
report={'schema':'mgs.archive.consumer.readonly.acceptance.v1','checked_at':storage.b.now_iso(),'task_id':'t_1b4f5263','request_id':reconciliation.REQUEST,'identity':storage.b.CANONICAL_SA,'checked':len(results),'passed':sum(x['passed'] for x in results),'failed':len(failed),'protected_file_sha256':protected,'installation_sha256':installation['after'],'selected_inventory_unchanged':True,'whole_inventory_unchanged_during_locked_acceptance':True,'inventory_changed_externally_since_installation':sha(inv)!=installation['inventory_sha256'],'inventory_sha256':sha(inv),'phase_observations':phases,'media_writes':0,'meta_calls':0,'native_pairs':native,'records':results,'acceptance_met':not failed}
storage.b.atomic_json(H/'canonical-consumers-accepted.json',report)
print(json.dumps({k:report[k] for k in ['checked','passed','failed','identity','selected_inventory_unchanged','whole_inventory_unchanged_during_locked_acceptance','media_writes','meta_calls','acceptance_met']}))
print(json.dumps(failed))
assert not failed,'consumer_failure'
assert not any(phases.values()),'unexpected_campaign_effects'
