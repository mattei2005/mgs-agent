"""Offline single-flight tests for the existing per-client immutable proof cache."""
import sys,json,time,threading,hashlib,unittest,copy
from pathlib import Path
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import ares_archive_bridge as b
import mgs_flat_source_compat as f
class ProofReadTests(unittest.TestCase):
 def fixtures(self):
  snapshot={'objects':{}};raw_snapshot=b.canonical(snapshot)
  receipt={'status':'verified','snapshot_sha256':hashlib.sha256(raw_snapshot).hexdigest(),'access_confirmation':'1566825959645253764'}
  raw_receipt=b.canonical(receipt)
  state={'redesign_confirmation':'1566814476626563115','access_confirmation':'1566825959645253764','snapshot_file_id':'fixture-snapshot','receipt_file_id':'fixture-receipt','snapshot_sha256':hashlib.sha256(raw_snapshot).hexdigest(),'receipt_sha256':hashlib.sha256(raw_receipt).hexdigest(),'control_folder_id':'fixture-control'}
  class Drive:
   def __init__(self):self.calls=[];self.guard=threading.Lock();self.corrupt=False
   def meta(self,fid):
    with self.guard:self.calls.append(('meta',fid))
    return {'lastModifyingUser':{'permissionId':b.PUBLISHER_PERMISSION_IDS[b.CANONICAL_SA]},'properties':{'mgsArchiveType':'stock_layout_snapshot'}}
   def raw(self,fid):
    with self.guard:self.calls.append(('raw',fid))
    time.sleep(.015)
    if self.corrupt:return b'wrong proof bytes'
    return raw_snapshot if fid=='fixture-snapshot' else raw_receipt
  return state,Drive()
 def test_concurrent_same_proof_is_verified_once_without_duplicate_gets(self):
  state,d=self.fixtures();barrier=threading.Barrier(4)
  def read(i):barrier.wait();return f.evidence(d,'fixture-source')
  with patch.object(f,'local_state',return_value=state),patch.object(b,'control_object_scope',return_value=True),ThreadPoolExecutor(max_workers=4) as pool:values=list(pool.map(read,range(4)))
  self.assertEqual(values,[values[0]]*4)
  self.assertEqual(len([x for x in d.calls if x[0]=='meta']),2)
  self.assertEqual(len([x for x in d.calls if x[0]=='raw']),2)
 def test_corrupt_proof_never_cached_and_later_verified_recovery(self):
  state,d=self.fixtures();d.corrupt=True
  with patch.object(f,'local_state',return_value=state),patch.object(b,'control_object_scope',return_value=True):
   with self.assertRaises(f.FlatSourceError):f.evidence(d,'fixture-source')
   self.assertFalse(getattr(d,'_flat_source_proof_cache',{}));d.corrupt=False
   self.assertEqual(len(f.evidence(d,'fixture-source')),2)
 def test_cache_never_shared_between_clients(self):
  state,d=self.fixtures();_,other=self.fixtures()
  with patch.object(f,'local_state',return_value=state),patch.object(b,'control_object_scope',return_value=True):f.evidence(d,'fixture-source');f.evidence(other,'fixture-source')
  self.assertEqual(len(d.calls),4);self.assertEqual(len(other.calls),4)
 def test_authority_still_rechecked_even_on_cache_hit(self):
  state,d=self.fixtures()
  with patch.object(f,'local_state',return_value=state),patch.object(b,'control_object_scope',return_value=True):
   f.evidence(d,'fixture-source');state['redesign_confirmation']='wrong'
   with self.assertRaises(f.FlatSourceError):f.evidence(d,'fixture-source')
if __name__=='__main__':unittest.main()
