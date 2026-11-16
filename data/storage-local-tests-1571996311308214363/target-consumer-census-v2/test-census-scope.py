"""In-memory scope/counter regressions; no application or destructive calls."""
import pathlib,json,copy,importlib.util
from unittest.mock import patch
OUT=pathlib.Path(__file__).parent
spec=importlib.util.spec_from_file_location('scoped_gate_tests',OUT/'gate.py');assert spec and spec.loader;g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
app=str(g.ROOT/'apps/finance-system/tests/census-in-memory.mjs');other=str(g.ROOT/'scripts/ares-unrelated-in-memory.py');jobs='/root/.hermes/profiles/ares/cron/jobs.json';new=other+'.new.py'
local={'id':'local-test','prompt':'inspect local PGlite data','enabled':True,'schedule':'daily','repeat':{'times':10,'completed':1}}
meta={'id':'meta-test','prompt':'read Meta page status','enabled':True,'schedule':'hourly','repeat':{'times':20,'completed':1}}
bodies={app:b'export const fixture=1',other:b'counter=1',jobs:json.dumps({'jobs':[local,meta]}).encode()};original=copy.deepcopy(bodies);passed=[]
def observe():
 with patch.object(g,'full_code_inventory',side_effect=lambda:{p:'not-used-global-digest'for p in bodies}),patch.object(pathlib.Path,'read_bytes',side_effect=None,autospec=True)as reader:
  reader.side_effect=lambda self:bodies[str(self)]
  return g.census()
def blocked(name):
 try:g.need(observe()==base,'CODE_OR_SCHEDULER_CENSUS_DRIFT')
 except RuntimeError:passed.append(name)
 else:raise AssertionError(name)
base=observe();assert app in base and other not in base and any('::job::local-test'in p for p in base)
bodies[other]=b'counter=2';assert observe()==base;passed.append('unrelated_code_edit_does_not_drift')
bodies[new]=b'counter=3';assert observe()==base;passed.append('unrelated_code_addition_does_not_drift');bodies.pop(new)
bodies[app]=b'export const fixture=2';blocked('finance_application_source_change_blocks');bodies[app]=original[app]
bodies[new]=b'import PGlite; generic_reader()';blocked('new_possible_DB_consumer_blocks');bodies.pop(new)
leaf=sorted(g.LEAVES)[0];bodies[other]=leaf.encode();blocked('exact_target_reference_even_in_unrelated_code_blocks');bodies[other]=original[other]
a=copy.deepcopy(local);b=copy.deepcopy(meta);b['enabled']=False;b['schedule']='weekly';b['repeat']['completed']=2;a['repeat']['completed']=2;bodies[jobs]=json.dumps({'jobs':[a,b]}).encode();assert observe()==base;passed.append('unrelated_job_definition_and_execution_counters_do_not_drift')
a['enabled']=False;bodies[jobs]=json.dumps({'jobs':[a,b]}).encode();blocked('relevant_job_definition_change_blocks')
a=copy.deepcopy(local);b['prompt']=leaf;bodies[jobs]=json.dumps({'jobs':[a,b]}).encode();blocked('new_job_with_exact_target_reference_blocks')
m=json.load(open(OUT/'manifest.json'));m['code_census_policy']='unknown'
try:g.shape(m)
except RuntimeError as exc:assert str(exc)=='CODE_CENSUS_POLICY';passed.append('unknown_census_policy_blocks')
else:raise AssertionError('unknown policy accepted')
r=dict(status='PASS',tests=len(passed),passed=passed,all_source_bodies_in_memory=True,real_source_data_deleted=0,application_code_executed=False)
(OUT/'census-regression-tests.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
