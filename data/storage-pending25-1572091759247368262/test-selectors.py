"""Selector boundaries and relevant-source regression, in memory only."""
import pathlib,json,importlib.util,copy
from unittest.mock import patch
OUT=pathlib.Path(__file__).parent
spec=importlib.util.spec_from_file_location('six_root_scope_tests',OUT/'gate.py');assert spec and spec.loader;g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g);passed=[]
source=str(g.BASE/'stage.mjs');initial=str(g.BASE/'stage-db');app_relative=str((g.BASE/'stage-db-v2').relative_to(g.ROOT/'apps/finance-system'))
cases=[('absolute_target',initial.encode(),'/external/script.py',True),('relative_APP_target',app_relative.encode(),'/external/script.py',True),('owner_module_relative',b"new URL('./stage-db-v3',import.meta.url)",source,True),('owner_id_composite',b"run='1552101423754514465';leaf='stage-db-v4'",'/external/script.py',True),('retained_v7_is_not_initial',b"new URL('./stage-db-v7',import.meta.url)",source,False),('retained_v7_absolute_not_prefix',(str(g.BASE/'stage-db-v7')).encode(),source,False),('other_owner_same_leaf',b"new URL('./stage-db',import.meta.url)",'/external/other/stage.mjs',False),('unrelated_suffix',b"'stage-db-v60'",source,False),('unrelated_prefix',b"'old-stage-db'",source,False),('target_descendant',(initial+'/pg_wal').encode(),source,True)]
for name,data,p,wanted in cases:assert g.target_selector(data,p)is wanted,name;passed.append(name)
app=str(g.ROOT/'apps/finance-system/tests/in-memory-selector.mjs');other=str(g.ROOT/'scripts/ares-unrelated-in-memory.py');jobs='/root/.hermes/profiles/ares/cron/jobs.json';extra=other+'.new.py';local={'id':'local','prompt':'inspect PGlite','enabled':True,'repeat':{'times':10,'completed':1}};meta={'id':'meta','prompt':'read Meta ads','enabled':True,'repeat':{'times':10,'completed':1}};bodies={app:b'export const fixture=1',other:b'counter=1',jobs:json.dumps({'jobs':[local,meta]}).encode()};original=copy.deepcopy(bodies)
def observe():
 with patch.object(g,'full_code_inventory',side_effect=lambda:{p:'not-used-broad-hash'for p in bodies}),patch.object(pathlib.Path,'read_bytes',autospec=True)as reader:
  reader.side_effect=lambda self:bodies[str(self)]
  return g.census()
def deny(name):
 try:g.need(observe()==baseline,'CODE_OR_SCHEDULER_CENSUS_DRIFT')
 except RuntimeError:passed.append(name)
 else:raise AssertionError(name)
baseline=observe();bodies[other]=b'counter=2';bodies[extra]=b'counter=3';assert observe()==baseline;passed.append('unrelated_code_change_and_addition_nonblocking');bodies.pop(extra)
bodies[app]=b'export const fixture=2';deny('relevant_app_change_blocks');bodies[app]=original[app]
bodies[extra]=b'import PGlite; read()';deny('new_possible_reader_blocks');bodies.pop(extra)
bodies[other]=initial.encode();deny('new_explicit_target_consumer_blocks');bodies[other]=original[other]
a=copy.deepcopy(local);b=copy.deepcopy(meta);a['repeat']['completed']=2;b['enabled']=False;bodies[jobs]=json.dumps({'jobs':[a,b]}).encode();assert observe()==baseline;passed.append('irrelevant_job_and_execution_counter_nonblocking')
a['enabled']=False;bodies[jobs]=json.dumps({'jobs':[a,b]}).encode();deny('relevant_job_change_blocks')
bodies[jobs]=json.dumps({'jobs':[dict(meta,prompt=initial)]}).encode();deny('explicit_target_job_blocks')
m=json.load(open(OUT/'manifest.json'));m['code_census_policy']='unknown'
try:g.shape(m)
except RuntimeError as e:assert str(e)=='CODE_CENSUS_POLICY';passed.append('wrong_code_policy_blocks')
else:raise AssertionError('wrong policy accepted')
r=dict(status='PASS',tests=len(passed),passed=passed,all_fixtures_in_memory=True,real_source_deletions=0,application_code_executed=False)
(OUT/'selector-regression-tests.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
