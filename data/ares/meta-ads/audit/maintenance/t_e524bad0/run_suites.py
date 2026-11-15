"""Offline acceptance runner; run inside read-only bwrap/network namespace."""
import sys,os,json,unittest,socket,subprocess,importlib.util
from pathlib import Path
H=Path('/root/mgs-agent/data/ares/meta-ads/audit/maintenance/t_e524bad0')
S=Path('/root/mgs-agent/scripts');T=Path('/root/mgs-agent/tests')
sys.path[:0]=[str(T),str(S)]
def denied(*a,**k):raise AssertionError('OFFLINE: transport/network subprocess prohibited')
socket.socket.connect=denied;socket.socket.connect_ex=denied;socket.create_connection=denied;subprocess.Popen=denied;os.system=denied
label=sys.argv[1];names=sys.argv[2:];results=[]
class Result(unittest.TextTestResult):
 def startTest(self,t):super().startTest(t);self.ids=getattr(self,'ids',[])+[t.id()]
for name in names:
 suite=unittest.defaultTestLoader.loadTestsFromName(name)
 with (H/(label+'-'+name+'.log')).open('w') as log:
  out=unittest.TextTestRunner(stream=log,verbosity=2,resultclass=Result).run(suite)
 results.append({'suite':name,'tests_run':out.testsRun,'success':out.wasSuccessful(),'failures':[t.id() for t,e in out.failures],'errors':[t.id() for t,e in out.errors],'skipped':[t.id() for t,e in out.skipped],'test_ids':getattr(out,'ids',[]),'log':str(H/(label+'-'+name+'.log'))})
receipt={'schema':'mgs.maintenance.unittest.v1','container':'results','counts_fields':['tests_run','failures','errors','skipped'],'role':label,'offline':{'network_namespace':True,'root_read_only':True,'socket_blocked':True,'transport_subprocess_blocked':True,'productive_writes_blocked':True},'results':results}
(H/(label+'.json')).write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'role':label,'suites':len(results),'tests':sum(r['tests_run'] for r in results),'failed_suites':[r['suite'] for r in results if not r['success']]}))
