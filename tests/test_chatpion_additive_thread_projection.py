import unittest,tempfile,importlib.util,json
from pathlib import Path
from unittest.mock import patch
import yaml
SCRIPT=Path('/root/mgs-agent/scripts/ares-chatpion-bot-strategy-sync.py')
def module():
 s=importlib.util.spec_from_file_location('sync_additive_test',SCRIPT);assert s and s.loader;m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
class AdditiveThreadProjectionTests(unittest.TestCase):
 def test_missing_thread_key_preserves_other_settings(self):
  m=module()
  with tempfile.TemporaryDirectory(dir='/root/.hermes/profiles/ares/cache/scratch') as tmp:
   p=Path(tmp)/'config.yaml';before={'model':'unchanged','discord':{'channel_prompts':{'one':'keep one','two':'keep two'},'other_setting':True},'terminal':{'backend':'local'}};p.write_text(yaml.safe_dump(before,sort_keys=False));text='New route\n- Page: exact\n- no implicit campaign permission'
   with patch.object(m,'VERSIONED_CONFIG',p):m.set_versioned_prompt('three',text)
   after=yaml.safe_load(p.read_text());expected=json.loads(json.dumps(before));expected['discord']['channel_prompts']['three']=text;self.assertEqual(after,expected)
 def test_missing_key_at_mapping_eof(self):
  m=module()
  with tempfile.TemporaryDirectory(dir='/root/.hermes/profiles/ares/cache/scratch') as tmp:
   p=Path(tmp)/'config.yaml';p.write_text('discord:\n  channel_prompts:\n    "one": before\n');text='New route\n- literal: scalar'
   with patch.object(m,'VERSIONED_CONFIG',p):m.set_versioned_prompt('two',text)
   self.assertEqual(yaml.safe_load(p.read_text())['discord']['channel_prompts'],{'one':'before','two':text})
 def test_projection_metadata_does_not_activate_candidates(self):
  m=module();reg={'consumers':{'one':{'status':'active'}},'onboarding_candidates':{'three':{'status':'read_only_pending'}},'naming_thread_projections':{'three':{'routes':{'campaign_creation':'123'}}}}
  self.assertEqual(set(m.selected_consumers(reg,'family',None)),{'one'});self.assertEqual(reg['onboarding_candidates']['three']['status'],'read_only_pending')
if __name__=='__main__':unittest.main()
