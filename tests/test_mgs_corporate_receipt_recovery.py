"""Offline recovered-receipt fixtures. Do not invent past destination metadata."""
import copy,contextlib,io,sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import mgs_corporate_archive as a
class RecoveredReceiptTests(unittest.TestCase):
 def fixture(self):
  p,s=a.load_plan();rid=s['root_id'];can=p['canary']
  root={'id':rid,'name':p['rootName'],'mimeType':a.b.FOLDER,'parents':[p['ownerRootId']],'createdTime':'2026-10-21T21:47:45.775Z','trashed':False,'owners':[{'emailAddress':p['account'],'permissionId':p['ownerPermissionId']}]}
  source={'id':can['id'],'name':can['name'],'mimeType':can['mimeType'],'createdTime':can['createdTime'],'parents':[a.b.SOURCE_DRIVE],'driveId':a.b.SOURCE_DRIVE,'trashed':False,'properties':{'validationOnly':'true'}}
  marker={'rootId':rid,'planSha256':s['plan_sha256'],'canaryRestored':True,'completedAt':'2026-10-21T21:49:12.000Z'}
  receipt={'schema':'mgs.corporate.setup.recovered.receipt.v1','status':'completed','authorizationMessageId':a.m.AUTH,'sharingConfirmationMessageId':a.APPROVAL,'planSha256':s['plan_sha256'],'priorWorkerSha256':'d92a531218ada431c7ed6ce90e5f9d2b3ecc8d53a2e59e8c626fa0976e3b1e49','root':root,'rootPermissions':a.desired(p),'deleteSource':False,'productionMutation':False,'infrastructureMutation':False,'productionContentMoved':False,'reconciledWithoutReplay':True,'canary':{'sourceId':can['id'],'restored':True,'proofMode':'protected_prior_worker_completion_marker','completionMarker':marker,'sourceAfter':{'metadata':source,'permissions':a.desired(p,True)}}}
  return p,s,receipt,rid
 def test_distinct_recovered_schema_does_not_require_invented_destination_snapshot(self):
  p,s,r,rid=self.fixture();self.assertEqual(a.validate_receipt(p,s,r),rid)
 def test_fabricated_destination_snapshot_is_rejected(self):
  p,s,r,_=self.fixture();r['canary']['destinationAfter']={'metadata':{}}
  with self.assertRaises(a.b.ArchiveError):a.validate_receipt(p,s,r)
 def test_fabricated_source_before_snapshot_is_rejected(self):
  p,s,r,_=self.fixture();r['canary']['sourceBefore']={'metadata':{}}
  with self.assertRaises(a.b.ArchiveError):a.validate_receipt(p,s,r)
 def test_other_root_cannot_use_targeted_recovery(self):
  p,s,r,_=self.fixture();r['root']['id']='OTHER_CORPORATE_ROOT'
  with self.assertRaises(a.b.ArchiveError):a.validate_receipt(p,s,r)
 def test_wrong_prior_digest_not_accepted(self):
  p,s,r,_=self.fixture();r['priorWorkerSha256']='0'*64
  with self.assertRaises(a.b.ArchiveError):a.validate_receipt(p,s,r)
 def test_marker_missing_is_not_success(self):
  p,s,r,_=self.fixture();r['canary'].pop('completionMarker')
  with self.assertRaises(a.b.ArchiveError):a.validate_receipt(p,s,r)
 def test_marker_time_must_fit_observed_prior_execution(self):
  p,s,r,_=self.fixture();r['canary']['completionMarker']['completedAt']='2026-10-22T00:00:00Z'
  with self.assertRaises(a.b.ArchiveError):a.validate_receipt(p,s,r)
 def test_live_source_role_cannot_be_silently_normalized(self):
  p,s,r,_=self.fixture();r['canary']['sourceAfter']['permissions'][0]['role']='writer'
  with self.assertRaises(a.b.ArchiveError):a.validate_receipt(p,s,r)
 def test_missing_service_account_root_editor_rejected(self):
  p,s,r,_=self.fixture();r['rootPermissions']=[x for x in r['rootPermissions'] if x['id']!='07414359829876449782']
  with self.assertRaises(a.b.ArchiveError):a.validate_receipt(p,s,r)
 def test_accept_cli_partial_state_is_nonzero_not_success(self):
  partial={'status':'corporate_root_acl_verified_owner_receipt_pending','grants_applied':True}
  with patch.object(sys,'argv',['mgs_corporate_archive.py','accept-setup']),patch.object(a.b,'queue_lock',contextlib.nullcontext),patch.object(a.b,'Drive',return_value=object()),patch.object(a.b,'config_load',return_value={}),patch.object(a,'verify_setup',return_value=partial),contextlib.redirect_stdout(io.StringIO()):self.assertEqual(a.main(),2)
if __name__=='__main__':unittest.main()
