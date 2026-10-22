"""Offline protocol fixtures only; never Google authorization/media proof."""
import sys,unittest,tempfile,copy,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import mgs_archive_owner_transport as t
import ares_archive_bridge as b
class ProtocolTests(unittest.TestCase):
 def setUp(self):
  self.c={'account':b.ACCOUNT,'source_drive_id':b.SOURCE_DRIVE,'source_root_id':b.SOURCE_ROOT,'archive_root_id':b.ARCHIVE_ROOT}
  self.asset={'role':'historical','sourceId':'OFFLINE_SOURCE01','sourceParentId':'OFFLINE_PARENT01','name':'fixture.jpg','mimeType':'image/jpeg','size':'3','md5':'a'*32,'sha256':'b'*64,'version':'1','relativeParent':['approved','01_READY'],'sourceCreatedTime':'2026-10-19T01:00:00Z'}
  self.stage={'migration_id':'fixture-migration','manifest_file_id':'OFFLINE_MANIFEST01','manifest_sha256':'c'*64}
  self.manifest={'migrationId':'fixture-migration','assets':[self.asset]}
  self.job={'schema':'mgs.archive.request.v1','kind':'backfill','account':b.ACCOUNT,'sourceDriveId':b.SOURCE_DRIVE,'sourceRootId':b.SOURCE_ROOT,'archiveRootId':b.ARCHIVE_ROOT,'deleteSource':False,'migrationId':self.stage['migration_id'],'manifestFileId':self.stage['manifest_file_id'],'manifestSha256':self.stage['manifest_sha256'],'assets':[self.asset]}
  import hashlib
  self.job['jobId']=hashlib.sha256(b.canonical(self.job)).hexdigest()[:32];self.job['createdAt']='2026-10-22T00:00:00Z'
  self.meta={'id':'OFFLINE_COPY01','name':'fixture.jpg','mimeType':'image/jpeg','size':'3','md5Checksum':'a'*32,'sha256Checksum':'b'*64,'parents':['OFFLINE_DEST01'],'trashed':False,'owners':[{'emailAddress':b.ACCOUNT,'permissionId':b.PUBLISHER_PERMISSION_IDS[b.ACCOUNT]}],'permissions':[{'type':'user','role':'owner','emailAddress':b.ACCOUNT}]}
 def test_frozen_job_accepted(self):self.assertTrue(t.validate_job(self.job,self.c,self.manifest,self.stage))
 def test_modified_frozen_asset_rejected(self):
  j=copy.deepcopy(self.job);j['assets'][0]['name']='changed.jpg'
  with self.assertRaises(b.ArchiveError):t.validate_job(j,self.c,self.manifest,self.stage)
 def test_wrong_job_digest_rejected(self):
  j=copy.deepcopy(self.job);j['jobId']='f'*32
  with self.assertRaisesRegex(b.ArchiveError,'JOB_DIGEST'):t.validate_job(j,self.c,self.manifest,self.stage)
 def test_scope_expansion_rejected(self):
  for field,value in [('account','wrong@example.invalid'),('archiveRootId','OFFLINE_WRONG01'),('deleteSource',True),('kind','corporate_move')]:
   j=copy.deepcopy(self.job);j[field]=value
   with self.subTest(field=field),self.assertRaises(b.ArchiveError):t.validate_job(j,self.c,self.manifest,self.stage)
 def test_duplicate_source_rejected(self):
  j=copy.deepcopy(self.job);j['assets']*=2
  with self.assertRaises(b.ArchiveError):t.validate_job(j,self.c,self.manifest,self.stage)
 def test_copy_native_identity_accepted(self):self.assertTrue(t.validate_copy(self.meta,self.asset,'OFFLINE_DEST01',self.c))
 def test_copy_scope_changes_rejected(self):
  for field,value in [('id',self.asset['sourceId']),('parents',['OFFLINE_WRONG01']),('trashed',True),('size','4'),('name','wrong.jpg'),('driveId',b.SOURCE_DRIVE),('sha256Checksum','c'*64)]:
   m=copy.deepcopy(self.meta);m[field]=value
   with self.subTest(field=field),self.assertRaises(b.ArchiveError):t.validate_copy(m,self.asset,'OFFLINE_DEST01',self.c)
 def test_public_or_domain_copy_rejected(self):
  for typ in ['anyone','domain']:
   m=copy.deepcopy(self.meta);m['permissions'].append({'type':typ})
   with self.subTest(typ=typ),self.assertRaises(b.ArchiveError):t.validate_copy(m,self.asset,'OFFLINE_DEST01',self.c)
 def test_wrong_native_owner_rejected(self):
  m=copy.deepcopy(self.meta);m['owners'][0]['permissionId']='WRONG'
  with self.assertRaises(b.ArchiveError):t.validate_copy(m,self.asset,'OFFLINE_DEST01',self.c)
 def test_path_traversal_rejected(self):
  for names in [['..'],['bad/name'],['bad\\name'],[''],['x\x00']]:
   with self.subTest(names=names),self.assertRaises(b.ArchiveError):t.validate_path(names)
 def test_request_type_is_not_visible_to_legacy_worker(self):self.assertNotIn(t.REQUEST_TYPE,['request','backfill_request'])
 def test_handoff_not_ready_before_drain(self):
  p={'phase':'draining','reserved_at':'2026-10-22T00:00:00Z'}
  self.assertFalse(t.drain_elapsed(p,'2026-10-22T00:06:59Z'));self.assertTrue(t.drain_elapsed(p,'2026-10-22T00:07:00Z'))
 def test_intent_prevents_blind_replay_after_unknown_copy(self):
  with tempfile.TemporaryDirectory() as d:
   journal=t.Journal(Path(d)/'state.json');journal.intent('copy:test',{'source':'OFFLINE_SOURCE01'})
   with self.assertRaisesRegex(b.ArchiveError,'AMBIGUOUS'):journal.allow_create('copy:test')
 def test_known_landed_id_survives_restart(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'state.json';journal=t.Journal(p);journal.intent('copy:test',{'source':'OFFLINE_SOURCE01'});journal.landed('copy:test','OFFLINE_COPY01');self.assertEqual(t.Journal(p).known_id('copy:test'),'OFFLINE_COPY01')
 def test_bound_intent_cannot_change_identity(self):
  with tempfile.TemporaryDirectory() as d:
   journal=t.Journal(Path(d)/'state.json');journal.intent('copy:test',{'source':'OFFLINE_SOURCE01'})
   with self.assertRaisesRegex(b.ArchiveError,'INTENT_BINDING'):journal.intent('copy:test',{'source':'OTHER'})
 def test_source_duplicate_selection_excludes_all_existing_jobs_and_mappings(self):
  a=copy.deepcopy(self.asset);other=copy.deepcopy(a);other['sourceId']='OFFLINE_SOURCE02'
  selected=t.select_canary([a,other],{a['sourceId']},set(),{a['sourceId'],other['sourceId']});self.assertEqual(selected['sourceId'],other['sourceId'])
 def test_live_lineage_preserves_canonical_identity(self):
  c={**self.c,'delete_source':False,'queue_enabled':False,'effective_after':'2026-10-20T14:00:00+00:00'}
  raw={**self.asset,'role':'original','sourceCreatedTime':'2026-10-22T00:00:00Z'};clean={**raw,'role':'clean','sourceId':'OFFLINE_SOURCE02'}
  j=b.make_request(c,[raw,clean],kind='lineage',lineage_id='OFFLINE_LINEAGE01');self.assertTrue(t.validate_job(j,c,self.manifest,self.stage))
  j['deleteSource']=True
  with self.assertRaises(b.ArchiveError):t.validate_job(j,c,self.manifest,self.stage)
 def test_vps_heartbeat_never_uses_legacy_digest_or_trigger(self):
  import ares_archive_automation as a
  c={**self.c,'owner_executor_mode':'vps','owner_executor_sha256':'d'*64};hb={'schema':'mgs.archive.private.owner.heartbeat.v1','workerSha256':'d'*64,'executor':'private-vps-v1','executorRunId':'e'*32,'status':'ok','blocked':[],'canaryAcknowledged':True,'deleteSource':False,'executedAt':'2026-10-22T00:00:00Z'}
  self.assertTrue(a.heartbeat_ready(hb,c,'2026-10-22T00:01:00Z'))
  self.assertFalse(a.heartbeat_ready({**hb,'workerSha256':'a'*64},c,'2026-10-22T00:01:00Z'))
  self.assertFalse(a.heartbeat_ready({**hb,'blocked':[{'reason':'offline test'}]},c,'2026-10-22T00:01:00Z'))
  self.assertFalse(a.heartbeat_ready(hb,c,'2026-10-22T01:01:00Z'))
 def test_historical_verifier_rejects_unknown_request_type_before_api(self):
  import ares_archive_backfill as h
  with self.assertRaises(b.ArchiveError):h.verify_job(None,self.c,self.job,request_type='arbitrary')
if __name__=='__main__':unittest.main()
