import importlib.util,json,os,socket,sys,unittest
from pathlib import Path
from unittest.mock import patch
R=Path('/root/mgs-agent');M=R/'data/ares/meta-ads/audit/maintenance/t_53c187db'
sys.path[:0]=[str(R),str(R/'scripts'),str(R/'tests')]
name=sys.argv[1];kind=sys.argv[2];os.environ['TARGET_MEDIA_CANDIDATE']='1' if kind=='candidate' else '0'
os.environ['HERMES_PROFILE']='ares';os.environ['HERMES_HOME']='/root/.hermes/profiles/ares'
real_spec=importlib.util.spec_from_file_location
if kind=='candidate':
 import ares_campaign_v3
 spec=real_spec('ares_campaign_v3.target_media_recovery',M/'target_media_recovery.py');v=importlib.util.module_from_spec(spec);sys.modules[spec.name]=v;spec.loader.exec_module(v)
def spec_for(name,path,*args,**kwargs):
 if kind=='candidate' and Path(path).resolve()==R/'scripts/ares-eggbev-target-clone.py':path=M/'ares-eggbev-target-clone.py'
 return real_spec(name,path,*args,**kwargs)
with patch.object(socket.socket,'connect',side_effect=AssertionError('offline maintenance network forbidden')),patch.object(importlib.util,'spec_from_file_location',side_effect=spec_for):
 suite=unittest.defaultTestLoader.loadTestsFromName(name)
 with (M/(kind+'-'+name+'.log')).open('w') as out:result=unittest.TextTestRunner(stream=out,verbosity=2).run(suite)
row={'suite':name,'tests':result.testsRun,'failures':[str(t) for t,_ in result.failures],'errors':[str(t) for t,_ in result.errors],'skipped':len(result.skipped),'success':result.wasSuccessful()}
print(json.dumps(row));sys.exit(0 if result.wasSuccessful() else 1)
