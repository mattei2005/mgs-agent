import json,socket,sys
from pathlib import Path
from unittest.mock import patch
import pytest
M=Path('/root/mgs-agent/data/ares/meta-ads/audit/maintenance/t_9700e988')
baseline=len(sys.argv)>1 and sys.argv[1]=='baseline'
if baseline:
    import importlib.util
    sys.path.insert(0,'/root/mgs-agent/scripts')
    import ares_campaign_v3
    spec=importlib.util.spec_from_file_location('ares_campaign_v3.target_continuation',M/'before/target_continuation.py')
    module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
    ares_campaign_v3.target_continuation=module
suffix='-baseline' if baseline else ''
with patch.object(socket.socket,'connect',side_effect=AssertionError('offline core tests forbid external network')):
    code=pytest.main(['-q','-p','no:cacheprovider','--basetemp',str(M/('pytest-temp'+suffix)),'--junitxml',str(M/('core-junit'+suffix+'.xml')),'tests/test_ares_campaign_engine_v3.py'])
sys.exit(code)
