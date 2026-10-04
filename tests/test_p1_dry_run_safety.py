import importlib.util,io,json,sys,unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch
s=importlib.util.spec_from_file_location('p1_safety',Path('/root/mgs-agent/scripts/mgs-p1-runner.py'));m=importlib.util.module_from_spec(s);sys.modules[s.name]=m;s.loader.exec_module(m)
class P1DryRunSafety(unittest.TestCase):
 def test_same_card_downloads_have_distinct_paths(self):
  from types import SimpleNamespace
  with patch.object(m.requests,'get',return_value=SimpleNamespace(status_code=200,content=b'synthetic')):
   first=m.ensure_card_local('https://example.com/card.png','same-card')
   second=m.ensure_card_local('https://example.com/card.png','same-card')
  self.assertNotEqual(first,second)
  self.assertEqual(Path(first).read_bytes(),b'synthetic')
  self.assertEqual(Path(second).read_bytes(),b'synthetic')
 def test_dry_run_never_enters_provider_taxonomy_or_wordpress(self):
  argv=['mgs-p1-runner','--site','eggbev','--rec-url','https://example.com/rec-card/','--dry-run']
  with patch.object(sys,'argv',argv),patch.object(m,'load_site',return_value={'domain':'eggbev.com','language':'en','country':'gb'}),patch.object(m,'load_p1_template_contract',return_value={'path':'synthetic-contract','contract_mode':'universal'}),patch.object(m,'wp_get_post',side_effect=AssertionError('dryrun reached Wordpress')),patch.object(m,'make_exact_featured',side_effect=AssertionError('dryrun reached provider')),patch.object(m,'resolve_taxonomy',side_effect=AssertionError('dryrun reached taxonomy')),patch.object(m,'get_public',side_effect=AssertionError('dryrun reached network')):
   out=io.StringIO()
   with redirect_stdout(out): rc=m.main()
   result=json.loads(out.getvalue())
  self.assertEqual(rc,0)
  self.assertEqual(result['mode'],'preflight_only')
  self.assertFalse(result['publication_ready'])
  self.assertFalse(result['content_generated'])
if __name__=='__main__':unittest.main()
