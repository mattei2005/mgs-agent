import json,os,socket,sys,unittest
from pathlib import Path
from unittest.mock import patch
R=Path('/root/mgs-agent');M=R/'data/ares/meta-ads/audit/maintenance/t_3950b5d9'
sys.path[:0]=[str(R),str(R/'scripts'),str(R/'tests')]
os.environ['HERMES_PROFILE']='ares';os.environ['HERMES_HOME']='/root/.hermes/profiles/ares'
name=sys.argv[1]
with patch.object(socket.socket,'connect',side_effect=AssertionError('offline maintenance external network forbidden')):
    suite=unittest.defaultTestLoader.loadTestsFromName(name)
    with (M/(name+'.log')).open('w') as log:result=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
row={'suite':name,'tests':result.testsRun,'failures':[str(t) for t,_ in result.failures],'errors':[str(t) for t,_ in result.errors],'skipped':len(result.skipped),'success':result.wasSuccessful()}
print(json.dumps(row))
sys.exit(0 if result.wasSuccessful() else 1)
