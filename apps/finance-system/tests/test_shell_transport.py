import os,sys,unittest,subprocess
from unittest.mock import patch
from pathlib import Path
import finance_release as release
class ShellTransport(unittest.TestCase):
 def test_roundtrips(self):
  for raw in [b'',b'a',b'ab',b'abc',bytes(range(256)),os.urandom(65536)]:
   encoded=release.shell_encode(raw)
   self.assertEqual(release.shell_decode(encoded),raw)
 def test_bad_encoding_rejected(self):
  for v in ['!!!!','abcd\n','abc','a===','YWJj$','☃']:
   with self.assertRaises((ValueError,UnicodeError)):release.shell_decode(v)
 def test_corrupted_reverse_hash_blocks(self):
  real=subprocess.run
  def run(cmd,**kwargs):
   if cmd==['base64','--decode']:return subprocess.CompletedProcess(cmd,0,b'corrupted')
   return real(cmd,**kwargs)
  with patch.object(release.subprocess,'run',side_effect=run),self.assertRaises(ValueError):release.shell_encode(b'not corrupted')
 def test_policies_and_fences_preserved(self):
  src=Path(release.__file__).read_text()
  self.assertNotIn('base64.b64encode',src)
  self.assertIn('protected_target_scope',src)
  self.assertIn("fence['phase']==v['phase']",src)
  self.assertIn('baseline_drift_no_changes',src)
  self.assertIn('missing_current_release_gate',src)
if __name__=='__main__':unittest.main()
