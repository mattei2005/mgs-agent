"""Strict unsealed-preparation equivalence; never a campaign approval."""
import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
import test_native_thumbnail_equivalence as fixtures
from ares_campaign_v3 import native_thumbnail_equivalence as native,eggbev_cross_account as cross

class PreparationThumbnailTests(unittest.TestCase):
 def setUp(self):
  self.a=fixtures.snapshot(fixtures.OLD);self.b=fixtures.snapshot(fixtures.NEW)
  self.context={'request_id':'offline-preparation-thumbnail','preparation_snapshot_sha256':native.digest(self.a),'account_id':'123','source_campaign_id':'456'}
 def call(self,fetcher=None):
  return native.compare_preparation(self.a,self.b,context=self.context,normalize=fixtures.runner.source_comparison,fetcher=fetcher or (lambda url:fixtures.JPEG))
 def test_preparation_receipt_is_not_manifest_approval(self):
  p=self.call();self.assertFalse(p['manifest_approval']);self.assertNotIn('approved_digest',p['context']);self.assertEqual(p['context'],self.context)
 def test_wrong_original_pin_denied(self):
  self.context['preparation_snapshot_sha256']='a'*64
  with self.assertRaises(ValueError):self.call()
 def test_different_bytes_denied(self):
  with self.assertRaises(ValueError):self.call(lambda url:fixtures.JPEG+url.encode())
 def test_other_source_delta_denied_before_download(self):
  self.b['adset']['targeting']['age_min']=25;fetch=Mock(return_value=fixtures.JPEG)
  with self.assertRaises(ValueError):self.call(fetch)
  fetch.assert_not_called()
 def test_input_snapshots_immutable(self):
  old=copy.deepcopy((self.a,self.b));self.call();self.assertEqual((self.a,self.b),old)
 def test_approved_context_not_accepted_as_preparation(self):
  self.context['approved_digest']=self.context.pop('preparation_snapshot_sha256')
  with self.assertRaises(ValueError):self.call()
 def test_cross_resume_preserves_first_snapshot_and_saves_evidence(self):
  self.a['campaign']['account_id']=self.b['campaign']['account_id']=cross.SOURCE
  with tempfile.TemporaryDirectory(dir='/root/.hermes/profiles/ares/cache/scratch') as tmp:
   h=Path(tmp);original=copy.deepcopy(self.a)
   with patch.object(native,'fetch_native',return_value=fixtures.JPEG):
    cross.require_source_consistency({'request_id':'offline-cross-preparation'},self.a,self.b,fixtures.runner,h)
   self.assertEqual(self.a,original);proofs=list(h.glob('thumbnail-equivalence-*.json'));self.assertEqual(len(proofs),1)
   self.assertFalse(json.loads(proofs[0].read_text())['manifest_approval'])
 def test_sealed_cross_resume_keeps_actual_approved_digest(self):
  self.a['campaign']['account_id']=self.b['campaign']['account_id']=cross.SOURCE
  with tempfile.TemporaryDirectory(dir='/root/.hermes/profiles/ares/cache/scratch') as tmp:
   with patch.object(native,'fetch_native',return_value=fixtures.JPEG):cross.require_source_consistency({'request_id':'offline-cross-preparation'},self.a,self.b,fixtures.runner,Path(tmp),'d'*64)
   p=json.loads(next(Path(tmp).glob('thumbnail-equivalence-*.json')).read_text());self.assertEqual(p['context']['approved_digest'],'d'*64)

if __name__=='__main__':unittest.main()
