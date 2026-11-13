import unittest, hashlib, os
from pathlib import Path
from codec import encode, decode, check_base
ROOT=Path(__file__).parent/'fixture';ROOT.mkdir(mode=0o700,exist_ok=True)
BASE=ROOT/'base.bin';TARGET=ROOT/'target.bin';WRONG=ROOT/'wrong.bin'
if not BASE.exists():
 data=os.urandom(512*1024);BASE.write_bytes(data);TARGET.write_bytes(data[:10000]+b'CHANGED-CONTENT'*100+data[11400:]+b'TAIL');WRONG.write_bytes(bytes(len(data)))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
class CodecTests(unittest.TestCase):
 def test_plain_roundtrip(self):self.assertEqual(decode(encode(TARGET),expected_size=TARGET.stat().st_size),TARGET.read_bytes())
 def test_delta_roundtrip(self):
  packed=encode(TARGET,BASE);self.assertEqual(decode(packed,BASE,sha(BASE),TARGET.stat().st_size),TARGET.read_bytes());self.assertLess(len(packed),TARGET.stat().st_size//4)
 def test_wrong_base_rejected_before_decode(self):
  with self.assertRaisesRegex(ValueError,'BASE_HASH_MISMATCH'):check_base(WRONG,sha(BASE))
 def test_corruption_rejected(self):
  packed=encode(TARGET,BASE);bad=packed[:-5]+bytes(x^255 for x in packed[-5:])
  with self.assertRaises(RuntimeError):decode(bad,BASE,sha(BASE),TARGET.stat().st_size)
 def test_truncation_rejected(self):
  packed=encode(TARGET,BASE)
  with self.assertRaises(RuntimeError):decode(packed[:len(packed)//2],BASE,sha(BASE),TARGET.stat().st_size)
 def test_inputs_unchanged(self):
  a,b=sha(BASE),sha(TARGET);decode(encode(TARGET,BASE),BASE,a,TARGET.stat().st_size);self.assertEqual((a,b),(sha(BASE),sha(TARGET)))
if __name__=='__main__':unittest.main()
