"""Offline corporate setup contract fixtures, never Google-side evidence."""
import copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import mgs_corporate_archive as a

class CorporateSetupTests(unittest.TestCase):
 def fixture(self):
  p,s=a.load_plan();wanted=a.desired(p);src=a.desired(p,True);rid='OFFLINE_CORPORATE_ROOT'
  root={'id':rid,'name':p['rootName'],'mimeType':a.b.FOLDER,'parents':[p['ownerRootId']],'trashed':False,'owners':[{'emailAddress':p['account'],'permissionId':p['ownerPermissionId']}]}
  can=p['canary'];source={'id':can['id'],'name':can['name'],'mimeType':can['mimeType'],'createdTime':can['createdTime'],'parents':[a.b.SOURCE_DRIVE],'driveId':a.b.SOURCE_DRIVE,'trashed':False,'properties':{'validationOnly':'true'}}
  dest=copy.deepcopy(source);dest.pop('driveId');dest['parents']=[rid];dest['owners']=[{'emailAddress':p['account'],'permissionId':p['ownerPermissionId']}]
  r={'schema':'mgs.corporate.setup.receipt.v1','status':'completed','authorizationMessageId':a.m.AUTH,'sharingConfirmationMessageId':a.APPROVAL,'planSha256':s['plan_sha256'],'root':root,'rootPermissions':wanted,'deleteSource':False,'productionMutation':False,'productionContentMoved':False,'infrastructureMutation':True,'canary':{'sourceId':can['id'],'restored':True,'sourceBefore':{'metadata':source,'permissions':src},'destinationAfter':{'metadata':dest,'permissions':wanted},'sourceAfter':{'metadata':copy.deepcopy(source),'permissions':copy.deepcopy(src)}}}
  return p,s,r,rid
 def test_exact_receipt_canary_and_four_principals_pass(self):
  p,s,r,rid=self.fixture();self.assertEqual(a.validate_receipt(p,s,r),rid)
 def test_extra_creative_collaborator_not_accepted(self):
  p,s,r,_=self.fixture();r['rootPermissions'].append({'id':'rogue','role':'writer','type':'user'})
  with self.assertRaises(a.b.ArchiveError):a.validate_receipt(p,s,r)
 def test_missing_sa_writer_not_accepted(self):
  p,s,r,_=self.fixture();r['rootPermissions']=[x for x in r['rootPermissions'] if x['id']!='07414359829876449782']
  with self.assertRaises(a.b.ArchiveError):a.validate_receipt(p,s,r)
 def test_wrong_root_parent_is_not_hidden_parent_compatibility(self):
  p,s,r,_=self.fixture();r['root']['parents']=[a.b.ARCHIVE_ROOT]
  with self.assertRaises(a.b.ArchiveError):a.validate_receipt(p,s,r)
 def test_canary_source_must_be_restored(self):
  p,s,r,_=self.fixture();r['canary']['restored']=False
  with self.assertRaises(a.b.ArchiveError):a.validate_receipt(p,s,r)
 def test_receipt_cannot_claim_canary_acl_with_only_owner(self):
  p,s,r,_=self.fixture();r['canary']['destinationAfter']['permissions']=r['canary']['destinationAfter']['permissions'][:1]
  with self.assertRaises(a.b.ArchiveError):a.validate_receipt(p,s,r)
 def test_wrong_source_role_not_normalized(self):
  p,s,r,_=self.fixture();r['canary']['sourceAfter']['permissions'][0]['role']='writer'
  with self.assertRaises(a.b.ArchiveError):a.validate_receipt(p,s,r)
 def test_contradictory_email_does_not_override_native_id(self):
  p,s,r,_=self.fixture();r['rootPermissions'][0]['emailAddress']='wrong@example.invalid'
  with self.assertRaises(a.b.ArchiveError):a.validate_receipt(p,s,r)
 def test_source_id_cannot_be_replaced_with_copied_sheet(self):
  p,s,r,_=self.fixture();r['canary']['destinationAfter']['metadata']['id']='OTHER_SHEET_ID'
  with self.assertRaises(a.b.ArchiveError):a.validate_receipt(p,s,r)
 def test_consent_pin_cannot_be_another_confirmation(self):
  p,s,r,_=self.fixture();r['sharingConfirmationMessageId']='different'
  with self.assertRaises(a.b.ArchiveError):a.validate_receipt(p,s,r)
 def test_old_root_cannot_be_used_as_corporate_root(self):
  p,s,r,_=self.fixture();r['root']['id']=a.b.ARCHIVE_ROOT
  with self.assertRaises(a.b.ArchiveError):a.validate_receipt(p,s,r)
 def test_composite_preserves_whole_previous_worker_prefix(self):
  p,s,_,_=self.fixture();raw=a.build_source(p,s);base=(a.b.BASE/'integrations/creative-archive-30tb/WorkerWholeDriveRecovery.js').read_bytes();self.assertTrue(raw.startswith(base));self.assertIn(s['plan_sha256'].encode(),raw)
if __name__=='__main__':unittest.main()
