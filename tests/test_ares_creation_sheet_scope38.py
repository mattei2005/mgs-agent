"""Regression tests for two accounts in the same monthly-report cell."""
import copy,json,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import test_ares_creation_sheet as base

class SheetScope38Tests(unittest.TestCase):
 p: dict
 accounts: list
 snapshot: dict
 @classmethod
 def setUpClass(cls):
  base.CreationSheetTests.setUpClass.__func__(cls)
 def test_multiple_accounts_sum_instead_of_overwrite(self):
  s=copy.deepcopy(self.snapshot)
  selected=[a for a in s['accounts'] if a['brand']=='Yolokfx' and a['manager_code']=='G002']
  self.assertEqual(len(selected),2)
  for i,a in enumerate(selected):a['campaigns']=[{'id':'fixture-'+str(i),'account_id':a['account_id'],'created_time':s['cutoff']}]
  d=base.m.snapshot_to_days(s,self.p,self.accounts)
  self.assertEqual(d[s['cutoff'][:10]]['cells']['Yolokfx|G002'],2)
 def test_added_account_prebaseline_is_added_once_not_discarded(self):
  s=copy.deepcopy(self.snapshot)
  for a in s['accounts']:a['campaigns']=[]
  a=next(a for a in s['accounts'] if a['account_id']=='1492168699397108')
  a['campaigns']=[{'id':'fixture-prebaseline-added','account_id':a['account_id'],'created_time':'2026-10-10T12:00:00-0400'}]
  d=base.m.snapshot_to_days(s,self.p,self.accounts)
  d,ledger=base.m.preserve_history(s,d,self.accounts,{})
  baseline=base.m.load(base.m.BASE/self.p['historical_baseline'])
  expected=baseline['sites']['Yolokfx']['daily']['2026-10-10']['G002']+1
  self.assertEqual(d['2026-10-10']['cells']['Yolokfx|G002'],expected)
  again,second=base.m.preserve_history(s,copy.deepcopy(d),self.accounts,ledger)
  self.assertEqual(again['2026-10-10']['cells']['Yolokfx|G002'],expected);self.assertEqual(ledger,second)
 def test_added_incomplete_account_blocks_sheet_write(self):
  s=copy.deepcopy(self.snapshot);next(a for a in s['accounts'] if a['account_id']=='1663268201836138')['complete']=False
  with self.assertRaisesRegex(AssertionError,'INCOMPLETE'):base.m.snapshot_to_days(s,self.p,self.accounts)
 def test_same_count_unknown_account_rejected(self):
  original=base.m.load;catalog=base.m.BASE/'data/ares/meta-ads/operations/SHEIN-US-DIRECT-accounts.json'
  changed=copy.deepcopy(original(catalog));changed['accounts'][0]['account_id']='9999999999999999'
  def load(p):return changed if Path(p)==catalog else original(p)
  with patch.object(base.m,'load',side_effect=load),patch.object(base.m.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout='{"allowed":true}')):
   with self.assertRaisesRegex(AssertionError,'UNAPPROVED_ACCOUNT_DRIFT'):base.m.selection(self.p)
 def test_exact_selection_passes(self):
  with patch.object(base.m.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout='{"allowed":true}')):self.assertEqual(len(base.m.selection(self.p)),38)
 def test_google_uses_canonical_helper_and_rejects_wrong_identity(self):
  import os
  auth=SimpleNamespace(load_env=lambda:None,load_service_account=lambda:{'type':'service_account','client_email':'wrong','project_id':'mgs-core-prod'})
  values={k:'service_account' for k in ('ARES_DRIVE_AUTH_MODE','MGS_DRIVE_AUTH_PRIMARY','MGS_GOOGLE_SHEETS_AUTH_MODE','MGS_META_APP_ROLES_GOOGLE_AUTH_MODE')}
  with patch.object(base.m,'module',return_value=auth),patch.dict(os.environ,values):
   with self.assertRaisesRegex(AssertionError,'SA_IDENTITY'):base.m.Google(self.p)

if __name__=='__main__':unittest.main()
