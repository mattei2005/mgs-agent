import unittest,tempfile,importlib.util,json,subprocess
from pathlib import Path
from unittest.mock import patch
import yaml
S='/root/mgs-agent/scripts/ares-chatpion-bot-strategy-sync.py'
def load():
 spec=importlib.util.spec_from_file_location('sync_scalar_test',S);assert spec and spec.loader;m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
class PromptScalarTests(unittest.TestCase):
 def run_case(self,*,oversize=False,wrong_readback=False):
  m=load()
  with tempfile.TemporaryDirectory(dir='/root/.hermes/profiles/ares/cache/scratch') as tmp:
   root=Path(tmp);prompt='Instruction\n- Mapping: text\n- [literal] and "quoted"\n';source=root/'prompt.txt';source.write_text(prompt);config=root/'versioned.yaml';config.write_text(yaml.safe_dump({'discord':{'channel_prompts':{'123':prompt.strip()}}}));state={'123':'old','other':('x'*121000 if oversize else 'preserve this exactly')};calls=[]
   def run(args,**kwargs):
    calls.append(args)
    if 'set' in args:
     self.assertEqual(args[-2],'discord.channel_prompts');v=json.loads(args[-1]);self.assertEqual(v['other'],state['other']);self.assertEqual(v['123'],prompt.strip());self.assertFalse(v['123'].startswith('"'));state.update(v);return subprocess.CompletedProcess(args,0,'','')
    output=dict(state)
    if wrong_readback and len(calls)>=3:output['other']='unexpected drift'
    return subprocess.CompletedProcess(args,0,json.dumps(output),'')
   with patch.object(m,'ROOT',root),patch.object(m,'VERSIONED_CONFIG',config),patch.object(m,'set_versioned_prompt'),patch.object(m.subprocess,'run',side_effect=run):
    result=m.sync_prompt('123',source)
   return result,state,calls
 def test_multiline_scalar_roundtrip_and_other_prompts_preserved(self):
  result,state,calls=self.run_case();self.assertTrue(result['source_equals_runtime']);self.assertTrue(result['source_equals_versioned']);self.assertEqual(state['other'],'preserve this exactly');self.assertEqual(len(calls),3)
 def test_typed_container_write_not_dynamic_leaf(self):
  _,_,calls=self.run_case();self.assertIn('--json',calls[0]);self.assertEqual(calls[1][-2],'discord.channel_prompts')
 def test_oversized_mapping_fails_without_set(self):
  with self.assertRaisesRegex(RuntimeError,'safe CLI argument size'):self.run_case(oversize=True)
 def test_other_prompt_readback_drift_fails(self):
  with self.assertRaisesRegex(RuntimeError,'unrelated prompts'):self.run_case(wrong_readback=True)
if __name__=='__main__':unittest.main()
