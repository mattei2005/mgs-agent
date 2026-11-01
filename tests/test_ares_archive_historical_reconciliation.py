"""Offline guards for bounded historical metadata reconciliation.
Fixtures do not represent native production evidence and never write it.
"""
import unittest,sys,hashlib
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import ares_archive_namespace as n
class HistoricalReconciliationGuards(unittest.TestCase):
 def setUp(self):
  self.rec={'source_id':'offlineSource001','archive_id':'offlineProvider001','stock_id':'offlineStock001','sha256':'offline-sha','md5':'offline-md5','size':'10','provider_parent_id':'offlineParent001','reconciliation_authority':n.HISTORICAL_AUTHORITY}
  native={**self.rec,'full_bytes_and_native_ack_verified':True}
  self.proof={'schema':'mgs.legacy.historical.native.verification.v1','authority_message_id':n.HISTORICAL_AUTHORITY,'all_passed':True,'records':[native]}
  self.extra={'schema':'mgs.archive.historical.metadata.reconciliation.v1','authority_message_id':n.HISTORICAL_AUTHORITY,'original_plan_sha256':'offline-plan','phase':'active','files':{'offlineProvider001':self.rec},'verification_sha256':hashlib.sha256(n.b.canonical(self.proof)).hexdigest()}
  self.value={'plan_sha256':'offline-plan','files':{}}
  self.plan={'usage_unproven_preserved':[{'stock_id':'offlineStock001'}]}
 def read(self,path,default=None):return self.extra if path==n.HISTORICAL else self.proof
 def call(self):
  self.value['historical_reconciliation_sha256']=hashlib.sha256(n.b.canonical(self.extra)).hexdigest()
  with patch.object(n.b,'read_json',side_effect=self.read):return n.historical_reconciliation(self.value,self.plan)
 def test_valid_exact_scope(self):self.assertEqual(self.call(),self.extra['files'])
 def test_no_extension_keeps_old_contract(self):self.assertEqual(n.historical_reconciliation(self.value,self.plan),{})
 def test_wrong_authority_rejected(self):
  self.extra['authority_message_id']='unapproved'
  with self.assertRaises(n.NamespaceError):self.call()
 def test_additional_stock_rejected(self):
  self.rec['stock_id']='outsideOffline002'
  with self.assertRaises(n.NamespaceError):self.call()
 def test_changed_hash_rejected(self):
  self.rec['sha256']='changed-offline-hash'
  with self.assertRaises(n.NamespaceError):self.call()
 def test_unverified_native_ack_rejected(self):
  self.proof['records'][0]['full_bytes_and_native_ack_verified']=False;self.extra['verification_sha256']=hashlib.sha256(n.b.canonical(self.proof)).hexdigest()
  with self.assertRaises(n.NamespaceError):self.call()
if __name__=='__main__':unittest.main()
