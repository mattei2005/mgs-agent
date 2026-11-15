import importlib.util,json,os,socket,sys,unittest
from pathlib import Path
from unittest.mock import patch
R=Path('/root/mgs-agent');M=R/'data/ares/meta-ads/audit/maintenance/t_84f0dd13'
sys.path[:0]=[str(R),str(R/'scripts'),str(R/'tests')]
os.environ['HERMES_PROFILE']='ares';os.environ['HERMES_HOME']='/root/.hermes/profiles/ares'
name=sys.argv[1];kind=sys.argv[2] if len(sys.argv)>2 else 'installed'
if kind in {'candidate','baseline'}:
 import ares_campaign_v3
 p=M/'shein_channel_authority.py' if kind=='candidate' else M/'before/shein_channel_authority.py'
 spec=importlib.util.spec_from_file_location('ares_campaign_v3.shein_channel_authority',p);module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module);ares_campaign_v3.shein_channel_authority=module
with patch.object(socket.socket,'connect',side_effect=AssertionError('offline maintenance external network forbidden')):
 suite=unittest.defaultTestLoader.loadTestsFromName(name)
 with (M/(kind+'-'+name+'.log')).open('w') as log:result=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
row={'suite':name,'tests':result.testsRun,'failures':[str(t) for t,_ in result.failures],'errors':[str(t) for t,_ in result.errors],'skipped':len(result.skipped),'success':result.wasSuccessful()}
print(json.dumps(row));sys.exit(0 if result.wasSuccessful() else 1)
