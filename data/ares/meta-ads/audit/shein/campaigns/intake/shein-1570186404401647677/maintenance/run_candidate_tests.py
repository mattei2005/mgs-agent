import sys,importlib.util
from pathlib import Path
sys.path[:0]=['/root/mgs-agent/scripts','/root/mgs-agent/tests','/root/mgs-agent']
import ares_campaign_v3
b=Path(__file__).parent
for name in ['shein_reviewed_targeting','reviewed_copy_targeting']:
 spec=importlib.util.spec_from_file_location('ares_campaign_v3.'+name,b/(name+'.py'))
 m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;setattr(ares_campaign_v3,name,m);spec.loader.exec_module(m)
import pytest
raise SystemExit(pytest.main(['-q',str(b/'test_reviewed_copy_targeting.py'),'/root/mgs-agent/tests/test_shein_reviewed_targeting.py','/root/mgs-agent/tests/test_shein_batch_continuation.py','/root/mgs-agent/tests/test_ares_campaign_engine_v3.py','/root/mgs-agent/tests/test_shein_now_intent.py']))
