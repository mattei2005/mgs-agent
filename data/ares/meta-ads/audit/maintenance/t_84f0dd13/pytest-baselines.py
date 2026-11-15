import importlib.util,json,os,socket,sys
from pathlib import Path
from unittest.mock import patch
import pytest
R=Path('/root/mgs-agent');M=R/'data/ares/meta-ads/audit/maintenance/t_84f0dd13'
os.environ['HERMES_PROFILE']='ares';os.environ['HERMES_HOME']='/root/.hermes/profiles/ares'
sys.path[:0]=[str(R/'scripts'),str(R/'tests')]
kind=sys.argv[1]
if kind in {'candidate','baseline'}:
 import ares_campaign_v3
 path=M/'shein_channel_authority.py' if kind=='candidate' else M/'before/shein_channel_authority.py'
 spec=importlib.util.spec_from_file_location('ares_campaign_v3.shein_channel_authority',path);module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module);ares_campaign_v3.shein_channel_authority=module
files=['tests/test_ares_campaign_engine_v3.py','tests/test_eggbev_creation_config_report.py','tests/test_shein_elapsed_continuation.py','tests/test_shein_immediate_start_prevention.py','tests/test_shein_rps_date_filter.py']
with patch.object(socket.socket,'connect',side_effect=AssertionError('offline network forbidden')):
 code=pytest.main(['-q','-p','no:cacheprovider','--basetemp',str(M/('pytest-'+kind)),'--junitxml',str(M/('pytest-'+kind+'.xml')),*files])
sys.exit(code)
