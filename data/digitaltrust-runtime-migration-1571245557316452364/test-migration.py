"""No business execution: actual resolver/imports, intercepted dispatch, blocked gates."""
import ast,copy,json,os,pathlib,runpy,subprocess,sys,types,unittest,datetime
from unittest.mock import patch
ROOT=pathlib.Path('/root/mgs-agent');OUT=pathlib.Path(__file__).parent
PREF=json.loads((OUT/'preflight.json').read_text());WHERE=pathlib.Path(os.environ.get('MGS_MIGRATION_TEST_SOURCE',str(ROOT/'scripts')))
H=WHERE/'meta-digital-trust-hourly40-run.py';A=WHERE/'meta-digital-trust-pc1-create-one.py'
CASES=[];REAL_RUN=subprocess.run
class Migration(unittest.TestCase):
 def setUp(self):
  self.h=runpy.run_path(str(H),run_name='migration_test_hourly');self.a=runpy.run_path(str(A),run_name='migration_test_adapter')
 def test_only_expected_ast_surface_changed(self):
  for current,row,allowed in [(H,PREF['files'][0],{'pc1_runtime_python','run_node'}),(A,PREF['files'][1],set())]:
   old=ast.parse(pathlib.Path(row['before']).read_text());new=ast.parse(current.read_text())
   old_funcs={x.name:ast.dump(x,include_attributes=False)for x in old.body if isinstance(x,(ast.FunctionDef,ast.AsyncFunctionDef))};new_funcs={x.name:ast.dump(x,include_attributes=False)for x in new.body if isinstance(x,(ast.FunctionDef,ast.AsyncFunctionDef))}
   self.assertEqual({k:v for k,v in old_funcs.items()if k not in allowed},{k:v for k,v in new_funcs.items()if k not in allowed})
   if current==H:
    o=next(x for x in old.body if isinstance(x,ast.FunctionDef)and x.name=='run_node');n=next(x for x in new.body if isinstance(x,ast.FunctionDef)and x.name=='run_node')
    class ReplaceInterpreter(ast.NodeTransformer):
     count=0
     def visit_Constant(self,node: ast.Constant) -> ast.AST:
      if node.value=='/root/.hermes/hermes-agent-port-main-46904a3b-mgs/.venv/bin/python':
       self.count+=1
       return ast.Call(func=ast.Name(id='pc1_runtime_python',ctx=ast.Load()),args=[],keywords=[])
      return node
    rewrite=ReplaceInterpreter();o=rewrite.visit(o)
    self.assertEqual(rewrite.count,1);self.assertEqual(ast.dump(o,include_attributes=False),ast.dump(n,include_attributes=False))
  CASES.append('AST proves all adapter business functions unchanged; runner changes interpreter only')
 def test_real_managed_resolver_and_imports(self):
  interpreter=self.h['pc1_runtime_python']();self.assertTrue(pathlib.Path(interpreter).is_file());self.assertNotIn('46904a3b',interpreter)
  home=pathlib.Path('/root/.hermes/profiles/zeus/cache/scratch/digitaltrust-migration-import-1571245557316452364');home.mkdir(mode=0o700,exist_ok=True)
  env=dict(os.environ,HERMES_HOME=str(home),PYTHONPATH=PREF['runtime'],PYTHONDONTWRITEBYTECODE='1');env.pop('HERMES_PROFILE',None)
  code="import inspect,json; from tools.computer_use_tool import handle_computer_use,release_computer_use_session; inspect.signature(handle_computer_use).bind({'action':'list_windows'},session_id='migration-import-only'); inspect.signature(release_computer_use_session).bind('migration-import-only'); print(json.dumps({'imports':'PASS','called_handler':False,'module':inspect.getsourcefile(handle_computer_use)}))"
  p=REAL_RUN([interpreter,'-B','-c',code],capture_output=True,text=True,env=env,cwd=PREF['runtime'],timeout=30);self.assertEqual(p.returncode,0,p.stderr[-500:]);d=json.loads(p.stdout);self.assertTrue(d['module'].startswith(PREF['runtime']+'/'));self.assertFalse(d['called_handler']);self.assertEqual(str(self.a['RUNTIME']),PREF['runtime'])
  CASES.append('Real managed interpreter selection and current-source imports/binding; no handler called')
 def test_blocked_and_completed_adapter_never_dispatch(self):
  fn=self.a['main'];g=fn.__globals__
  def forbidden(*a,**kw):raise AssertionError('PC1/lease subprocess forbidden in test')
  with patch.object(sys,'argv',['migration-test']),patch.dict(g,{'subprocess':types.SimpleNamespace(run=forbidden)}):
   for filename in ['meta-digital-trust-40-20261007-state.json','meta-digital-trust-49-20261013-state.json']:
    g['STATE']=ROOT/'data'/filename;self.assertEqual(fn(),{'kind':'blocked','reason':'checkpoint_not_executable'});CASES.append(filename+': real gate blocked, zero subprocess calls')
 def test_adapter_identity_defaults_future_guards(self):
  fn=self.a['main'];g=fn.__globals__;p=ROOT/'data/meta-digital-trust-49-20261013-state.json';state=json.loads(p.read_text());g['STATE']=p
  def forbidden(*a,**kw):raise AssertionError('PC1/lease subprocess forbidden in test')
  with patch.object(sys,'argv',['migration-test']),patch.dict(g,{'subprocess':types.SimpleNamespace(run=forbidden)}):
   bad=copy.deepcopy(state);bad['request_id']='synthetic_wrong_request'
   with patch.object(pathlib.Path,'read_text',return_value=json.dumps(bad)):
    with self.assertRaisesRegex(RuntimeError,'contract_identity_mismatch'):fn()
   CASES.append('Synthetic wrong identity rejected before dispatch')
   bad=copy.deepcopy(state);bad['account_defaults']={}
   with patch.object(pathlib.Path,'read_text',return_value=json.dumps(bad)):
    with self.assertRaisesRegex(RuntimeError,'contract_defaults_mismatch'):fn()
   CASES.append('Synthetic changed account defaults rejected before dispatch')
   future=copy.deepcopy(state);future.update(status='scheduled',start_at='2999-01-01T00:00:00+00:00',next_due_at='2999-01-01T00:00:00+00:00')
   with patch.object(pathlib.Path,'read_text',return_value=json.dumps(future)):self.assertEqual(fn(),{'kind':'deferred','reason':'before_authorized_window','side_effect':'none'})
   CASES.append('Synthetic future window deferred before dispatch')
 def test_pc1_command_and_timeout_interception(self):
  fn=self.h['run_node'];g=fn.__globals__;calls=[]
  def fake_run(command,**kwargs):
   if len(command)>=4 and command[1:4]==['-I','-B','-c']:
    self.assertIn('from pm.environments import project_python',command[4]);return REAL_RUN(command,**kwargs)
   calls.append((command,kwargs));self.assertTrue(pathlib.Path(command[0]).is_file());self.assertNotIn('46904a3b',command[0]);self.assertEqual(command[1],str(ROOT/'scripts/meta-digital-trust-pc1-create-one.py'));return types.SimpleNamespace(returncode=0,stdout=json.dumps({'kind':'synthetic_dispatch_intercepted'}))
  with patch.dict(g,{'subprocess':types.SimpleNamespace(run=fake_run),'load_env':lambda:{'SYNTHETIC_TEST':'1'}}):
   for filename in ['meta-digital-trust-40-20261007-state.json','meta-digital-trust-49-20261013-state.json']:
    g['STATE_PATH']=ROOT/'data'/filename
    for preflight in [False,True]:
     self.assertEqual(fn(preflight),{'kind':'synthetic_dispatch_intercepted'});cmd,kwargs=calls[-1];self.assertEqual('--preflight'in cmd,preflight);self.assertEqual(kwargs['timeout'],480);CASES.append(filename+': intercepted command/timeout, preflight='+str(preflight))
 def test_wrong_pc1_scope_never_dispatches(self):
  fn=self.h['run_node'];g=fn.__globals__;state=json.loads((ROOT/'data/meta-digital-trust-49-20261013-state.json').read_text());state['business_id']='synthetic_wrong_business';g['STATE_PATH']=ROOT/'data/meta-digital-trust-49-20261013-state.json'
  def forbidden(*a,**kw):raise AssertionError('Resolver and subprocess forbidden for wrong scope')
  with patch.dict(g,{'pc1_runtime_python':forbidden}),patch.object(pathlib.Path,'read_text',return_value=json.dumps(state)):
   self.assertEqual(fn(),{'kind':'blocked','reason':'pc1_backend_scope_mismatch'})
  CASES.append('Wrong PC1 scope refused before interpreter resolution')
 def test_legacy_node_route_preserved(self):
  fn=self.h['run_node'];g=fn.__globals__;g['STATE_PATH']=ROOT/'data/meta-digital-trust-hourly40-20260906-state.json'
  def intercept(command,**kwargs):
   self.assertEqual(command,['node',str(ROOT/'scripts/meta-digital-trust-create-one.js')]);self.assertEqual(kwargs['timeout'],240);return types.SimpleNamespace(returncode=0,stdout=json.dumps({'kind':'synthetic_legacy_dispatch_intercepted'}))
  with patch.dict(g,{'subprocess':types.SimpleNamespace(run=intercept),'load_env':lambda:{'SYNTHETIC_TEST':'1'}}):self.assertEqual(fn(),{'kind':'synthetic_legacy_dispatch_intercepted'})
  CASES.append('Legacy Node command and 240s timeout unchanged; dispatch intercepted')
if __name__=='__main__':
 suite=unittest.defaultTestLoader.loadTestsFromTestCase(Migration);result=unittest.TextTestRunner(verbosity=1).run(suite);receipt={'status':'PASS'if result.wasSuccessful()else'FAIL','source':str(WHERE),'unit_tests_run':result.testsRun,'asserted_scenarios':CASES,'scenario_count':len(CASES),'errors':len(result.errors),'failures':len(result.failures),'business_pc1_calls':0,'live_business_preflight_executed':False,'finished_at':datetime.datetime.now().astimezone().isoformat()};tag='staged'if str(WHERE)==PREF['stage']else'deployed';(OUT/('tests-'+tag+'.json')).write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt));raise SystemExit(0 if result.wasSuccessful()else 1)
