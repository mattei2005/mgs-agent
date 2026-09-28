import copy,json,pathlib,sys,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from august_reconciliation import yolo_metadata,YOLO_POLICY_ID,YOLO_AUTHORITY
class AugustYolokfxOwnerTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.data=json.loads((ROOT/'private/source.json').read_text())
 def policy(self):return {'kind':'reconciliation_policy','id':YOLO_POLICY_ID,'authorization':YOLO_AUTHORITY}
 def test_inactive_policy_preserves_identity(self):
  for p in ['2026-08','2026-09','2027-12']:self.assertIs(yolo_metadata(self.data,[],p),self.data)
 def test_august_changes_only_two_metadata_fields(self):
  original=copy.deepcopy(self.data);after=yolo_metadata(self.data,[self.policy()],'2026-08');self.assertEqual(self.data,original)
  changed=[(a,b) for a,b in zip(self.data['cells'],after['cells']) if a!=b];self.assertEqual(len(changed),1);self.assertEqual(changed[0][1]['input'],'SEM_COMISSAO')
  row=changed[0][1]['cell'][1:];h=[c for c in after['cells'] if c['book']=='principal' and c['sheet']=='BASE_DASH' and c['cell']=='H'+row];self.assertLessEqual(len(h),1)
  if h:self.assertEqual(h[0]['input'],'MGS')
  for a,b in changed:self.assertEqual(a['sheet'],'BASE_DASH');self.assertEqual({k:v for k,v in a.items() if k!='input'},{k:v for k,v in b.items() if k!='input'})
 def test_other_periods_rejected(self):
  for p in ['2026-07','2026-09','2027-12']:
   with self.assertRaises(ValueError):yolo_metadata(self.data,[self.policy()],p)
 def test_wrong_authority_rejected(self):
  with self.assertRaises(ValueError):yolo_metadata(self.data,[{**self.policy(),'authorization':'invalid'}],'2026-08')
 def test_duplicate_policy_rejected(self):
  with self.assertRaises(ValueError):yolo_metadata(self.data,[self.policy(),self.policy()],'2026-08')
if __name__=='__main__':unittest.main()
