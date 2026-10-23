"""Offline backup transfer constraints; not native Google proof."""
import sys,unittest,copy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import mgs_private_backup_transport as t
class BackupContractTests(unittest.TestCase):
 def setUp(self):
  self.p={'authorizationMessageId':'authority','migrationAuthorizationMessageId':'migration','bindingSha256':'a'*64,'futureCreatedNotBefore':'2026-10-20T00:00:00Z','tiers':{'daily':{'sourceId':'OFFLINE_SOURCE_PARENT','archiveId':'OFFLINE_ARCHIVE_PARENT'}},'pilotId':'OFFLINE_PILOT'}
  self.a={'sourceId':'OFFLINE_BINARY01','sourceParentId':'OFFLINE_SOURCE_PARENT','destinationParentId':'OFFLINE_ARCHIVE_PARENT','tier':'daily','mode':'full','name':'mgs-dr-daily-20261022T000000Z.zip.gpg','mimeType':'application/pgp-encrypted','size':'10','version':'1','md5':'b'*32,'sha256':'c'*64,'sourceCreatedTime':'2026-10-22T00:00:00Z','managedProperties':{'mgs_dr':'true','tier':'daily','mode':'full','sha256':'c'*64}}
  self.j={'schema':'mgs.backup.move.request.v1','jobId':t.a.job_id(self.p,self.a),'authorizationMessageId':'authority','migrationAuthorizationMessageId':'migration','bindingSha256':'a'*64,'planSha256':'d'*64,'asset':self.a,'receiptFileId':'OFFLINE_RECEIPT01','deleteSource':False,'archiveTrashEnabled':False}
 def test_approved_future_exact_id_job(self):self.assertTrue(t.validate_job(self.j,self.p,'d'*64))
 def test_foreign_parent_delete_or_changed_job_rejected(self):
  for field,value in [('sourceParentId','OTHER_PARENT'),('destinationParentId','OTHER_PARENT'),('sourceId','OFFLINE_PILOT'),('sha256','e'*64)]:
   j=copy.deepcopy(self.j);j['asset'][field]=value
   with self.subTest(field=field),self.assertRaises(t.b.ArchiveError):t.validate_job(j,self.p,'d'*64)
  for field in ['deleteSource','archiveTrashEnabled']:
   j=copy.deepcopy(self.j);j[field]=True
   with self.assertRaises(t.b.ArchiveError):t.validate_job(j,self.p,'d'*64)
 def test_move_state_never_blindly_replays(self):
  self.assertEqual(t.move_decision({'driveId':t.b.SOURCE_DRIVE,'parents':[self.a['sourceParentId']]},self.a,False),'move_once')
  with self.assertRaises(t.b.ArchiveError):t.move_decision({'driveId':t.b.SOURCE_DRIVE,'parents':[self.a['sourceParentId']]},self.a,True)
  self.assertEqual(t.move_decision({'parents':[self.a['destinationParentId']]},self.a,True),'reconcile_landed')
  with self.assertRaises(t.b.ArchiveError):t.move_decision({'parents':['OUTSIDE']},self.a,True)
 def test_historical_requires_its_exact_additional_manifest(self):
  j=copy.deepcopy(self.j);j['asset']['sourceCreatedTime']='2026-09-01T00:00:00Z';j['jobId']=t.a.job_id(self.p,j['asset'])
  with self.assertRaises(t.b.ArchiveError):t.validate_job(j,self.p,'d'*64)
  manifest={'approval_message_id':t.APPROVAL,'plan_sha256':'d'*64,'assets':[j['asset']]};j.update(wholeDriveAuthorizationMessageId=t.APPROVAL,historicalManifestSha256=t.a.sha(manifest))
  self.assertTrue(t.validate_job(j,self.p,'d'*64,manifest))
  with self.assertRaises(t.b.ArchiveError):t.validate_job(j,self.p,'d'*64)
  j['historicalManifestSha256']='e'*64
  with self.assertRaises(t.b.ArchiveError):t.validate_job(j,self.p,'d'*64,manifest)
if __name__=='__main__':unittest.main()
