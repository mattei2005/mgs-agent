"""Qualification regressions: retained cloud bytes alone cannot admit a media file into this final lot."""
import pathlib,json,copy,importlib.util,unittest
from unittest.mock import patch
O=pathlib.Path(__file__).parent;spec=importlib.util.spec_from_file_location('g',O/'gate.py');assert spec and spec.loader;g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g);m,d=g.load_manifest();old=json.loads((O.parent/'manifest.json').read_text());media=[r for r in old['targets']if r['kind']=='archived_media']
class QualificationTests(unittest.TestCase):
 def test_one_cloud_recoverable_media_still_not_eligible(self):
  changed=copy.deepcopy(m);changed['targets'][0]=media[0]
  with self.assertRaisesRegex(RuntimeError,'KIND_COUNTS'):g.shape(changed)
 def test_owner_closure_drift_blocks(self):
  hashes={**m['evidence_hashes'],**m['reader_source_hashes']}
  with patch.object(g,'sha',side_effect=lambda p:hashes[str(p)]),patch.object(pathlib.Path,'read_text',return_value='{"checkpoints":[]}'):
   with self.assertRaisesRegex(RuntimeError,'OWNER_CLOSURE_CHANGED'):g.verify_source_evidence(m)
result=unittest.TextTestRunner().run(unittest.defaultTestLoader.loadTestsFromTestCase(QualificationTests));assert result.wasSuccessful();retained={r['path']for r in m['retained_files']};assert len(media)==304 and all(r['path']in retained for r in media);assert not set(r['path']for r in media)&set(r['path']for r in m['targets']);receipt={'status':'PASS','qualification_tests':result.testsRun,'all304_media_explicitly_retained':True,'target_media_overlap':0,'source_files_deleted':0};out=O/'qualification-tests.json'
if out.exists():assert json.loads(out.read_text())==receipt
else:out.write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt))
