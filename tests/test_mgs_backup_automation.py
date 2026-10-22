"""Offline protocol fixtures; these tests are not Google execution proof."""
import copy,sys,unittest,importlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
class BackupAutomationTests(unittest.TestCase):
 def setUp(self):
  self.a=importlib.import_module('mgs_backup_automation')
  self.p={'bindingSha256':'d'*64,'sourceDriveId':self.a.b.SOURCE_DRIVE,'account':self.a.b.ACCOUNT,'corporateRootId':'corpRoot123','archiveRootId':'archiveRoot123','sourceRootId':'sourceRoot123','futureCreatedNotBefore':'2026-10-22T05:00:00+00:00','authorizationMessageId':'1562688137472249867','migrationAuthorizationMessageId':self.a.m.AUTH,'retentionCount':{'hourly':48,'daily':14,'weekly':8,'monthly':12},'tiers':{t:{'sourceId':'source'+t,'archiveId':'archive'+t} for t in self.a.TIERS},'deleteSource':False,'archiveTrashEnabled':False}
  self.meta={'id':'sourceFile123','name':'mgs-dr-hourly-20261022T052300Z.zip.gpg','mimeType':'application/pgp-encrypted','createdTime':'2026-10-22T05:23:00Z','parents':['sourcehourly'],'driveId':self.a.b.SOURCE_DRIVE,'trashed':False,'size':'1234','md5Checksum':'a'*32,'sha256Checksum':'b'*64,'version':'1','appProperties':{'mgs_dr':'true','sha256':'b'*64,'tier':'hourly','mode':'quick'}}
 def test_future_managed_binary_accepted(self):self.a.backup_asset(self.meta,self.p,'hourly')
 def test_old_backup_cannot_enter_future_lane(self):
  self.meta['createdTime']='2026-10-21T23:00:00Z'
  with self.assertRaises(self.a.b.ArchiveError):self.a.backup_asset(self.meta,self.p,'hourly')
 def test_wrong_parent_rejected(self):
  self.meta['parents']=['sourceweekly']
  with self.assertRaises(self.a.b.ArchiveError):self.a.backup_asset(self.meta,self.p,'hourly')
 def test_missing_managed_marker_rejected(self):
  self.meta['appProperties'].pop('mgs_dr')
  with self.assertRaises(self.a.b.ArchiveError):self.a.backup_asset(self.meta,self.p,'hourly')
 def test_private_sha_does_not_replace_native_sha(self):
  self.meta.pop('sha256Checksum')
  with self.assertRaises(self.a.b.ArchiveError):self.a.backup_asset(self.meta,self.p,'hourly')
 def test_wrong_encryption_mime_rejected(self):
  self.meta['mimeType']='application/octet-stream'
  with self.assertRaises(self.a.b.ArchiveError):self.a.backup_asset(self.meta,self.p,'hourly')
 def test_wrong_mode_rejected(self):
  self.meta['appProperties']['mode']='full'
  with self.assertRaises(self.a.b.ArchiveError):self.a.backup_asset(self.meta,self.p,'hourly')
 def test_job_identity_stable_and_content_bound(self):
  a=self.a.backup_asset(self.meta,self.p,'hourly');self.assertEqual(self.a.job_id(self.p,a),self.a.job_id(self.p,copy.deepcopy(a)));a['sha256']='c'*64;self.assertNotEqual(self.a.job_id(self.p,a),self.a.job_id(self.p,self.a.backup_asset(self.meta,self.p,'hourly')))
 def test_forward_version_is_allowed_only_with_frozen_bytes(self):
  a=self.a.backup_asset(self.meta,self.p,'hourly');self.meta['version']='3';self.a.check_content(self.meta,a)
  self.meta['sha256Checksum']='c'*64
  with self.assertRaises(self.a.b.ArchiveError):self.a.check_content(self.meta,a)
 def test_backward_version_is_rejected(self):
  self.meta['version']='3';a=self.a.backup_asset(self.meta,self.p,'hourly');self.meta['version']='2'
  with self.assertRaises(self.a.b.ArchiveError):self.a.check_content(self.meta,a)
 def test_retention_preview_never_proposes_source_trash(self):
  rows=[{'id':str(i),'tier':'hourly','createdTime':f'2026-10-22T00:{i:02d}:00Z','location':'source','verified':False} for i in range(50)]
  out=self.a.retention_preview(rows,self.p,protected_ids=set());self.assertEqual(out['archive_trash_candidates'],[]);self.assertEqual(len(out['source_expired_preserved']),2);self.assertFalse(out['deletion_enabled'])
 def test_retention_preserves_last_restored_generation(self):
  self.p['retentionCount']['weekly']=1;rows=[{'id':'old','tier':'weekly','createdTime':'2026-10-18T00:00:00Z','location':'archive','verified':True},{'id':'new','tier':'weekly','createdTime':'2026-10-25T00:00:00Z','location':'archive','verified':True}]
  out=self.a.retention_preview(rows,self.p,protected_ids={'old'});self.assertEqual(out['archive_trash_candidates'],[]);self.assertEqual(out['protected_expired'],['old'])
 def test_unverified_archive_never_becomes_trash_candidate(self):
  self.p['retentionCount']['weekly']=1;rows=[{'id':'old','tier':'weekly','createdTime':'2026-10-18T00:00:00Z','location':'archive','verified':False},{'id':'new','tier':'weekly','createdTime':'2026-10-25T00:00:00Z','location':'archive','verified':True}]
  out=self.a.retention_preview(rows,self.p,protected_ids=set());self.assertEqual(out['archive_trash_candidates'],[]);self.assertEqual(out['unverified_expired'],['old'])
 def test_preview_only_candidates_are_scoped_archives(self):
  self.p['retentionCount']['weekly']=1;rows=[{'id':'old','tier':'weekly','createdTime':'2026-10-18T00:00:00Z','location':'archive','verified':True},{'id':'new','tier':'weekly','createdTime':'2026-10-25T00:00:00Z','location':'archive','verified':True}];out=self.a.retention_preview(rows,self.p,protected_ids=set());self.assertEqual(out['archive_trash_candidates'],['old']);self.assertFalse(out['deletion_enabled'])
 def test_duplicate_native_ids_are_rejected(self):
  row={'id':'same','tier':'weekly','createdTime':'2026-10-18T00:00:00Z','location':'archive','verified':True}
  with self.assertRaises(self.a.b.ArchiveError):self.a.retention_preview([row,row],self.p,protected_ids=set())
 def test_unresolved_job_publication_never_posts_again(self):
  from unittest.mock import Mock,patch
  d=Mock();d.one.return_value=None;body={'fixture':'offline'};state={'publications':{'key':{'sha256':self.a.sha(body),'status':'intent'}}}
  with patch.object(self.a.b,'atomic_json'):
   with self.assertRaisesRegex(self.a.b.ArchiveError,'NO_REPLAY'):self.a.immutable(d,'parent123','key','backup_ack',body,state)
  d.upload_once.assert_not_called()
 def test_unresolved_staged_worker_publication_never_posts_again(self):
  from unittest.mock import Mock,patch
  d=Mock();d.one.return_value=None;stage={'publication_intents':{'key':{'sha256':self.a.sha(b'offline'),'status':'intent'}}}
  with patch.object(self.a.b,'atomic_json'):
   with self.assertRaisesRegex(self.a.b.ArchiveError,'NO_REPLAY'):self.a.staged_blob(d,stage,'parent123','key','worker_source',b'offline','offline.js','application/javascript')
  d.upload_once.assert_not_called()
 def test_heartbeat_without_timestamp_is_not_ready(self):self.assertFalse(self.a.owner_ready({}, {},self.p))
 def test_same_worker_manual_heartbeat_is_not_scheduled_proof(self):
  hb={'executedAt':self.a.b.now_iso(),'workerSha256':'e'*64,'triggerUid':None,'status':'ok','blocked':[],'deleteSource':False,'canaryAcknowledged':True};self.assertFalse(self.a.owner_ready(hb,{'worker_sha256':'e'*64,'plan_sha256':'f'*64},self.p))
if __name__=='__main__':unittest.main()
