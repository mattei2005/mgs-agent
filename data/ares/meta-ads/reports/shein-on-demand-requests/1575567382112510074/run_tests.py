import json,re,subprocess,sys
from pathlib import Path
R=Path(__file__).parent
argv=json.loads(subprocess.check_output(['/root/.local/bin/hermes','--print-runtime-command'],text=True))
expected="runpy.run_module('hermes_cli.main', run_name='__main__', alter_sys=True)"
assert argv[-1].count(expected)==1
suites=[]
for name in ['test_shein_report_financial_source.py','test_shein_report_layout.py','test_shein_report_intraday.py','test_shein_report_daily_d1.py']:
 cmd=list(argv)
 testdir=str(R/'scoped-tests') if name=='test_shein_report_financial_source.py' else '/root/.hermes/profiles/ares/tests'
 code="sys.argv=['unittest','discover','-s',"+repr(testdir)+",'-p',"+repr(name)+"];runpy.run_module('unittest',run_name='__main__',alter_sys=True)"
 cmd[-1]=cmd[-1].replace(expected,code,1)
 p=subprocess.run(cmd,capture_output=True,text=True)
 out=p.stdout+p.stderr
 (R/(name+'.log')).write_text(out)
 match=re.search(r'Ran (\d+) tests?',out)
 suites.append({'suite':name,'returncode':p.returncode,'tests_run':int(match[1]) if match else None,'test_source':testdir,'adaptation':'task-local binding uniqueness and catalog subset; catalog-only accounts do not imply report bindings' if name=='test_shein_report_financial_source.py' else None})
 print(json.dumps(suites[-1]),flush=True)
 if p.returncode: print(out);raise SystemExit(p.returncode)
(R/'test-results.json').write_text(json.dumps({'suites':suites},indent=2))
cmd=list(argv);cmd[-1]=cmd[-1].replace(expected,"sys.argv=["+repr(str(R/'test_summary.py'))+"];runpy.run_path(sys.argv[0],run_name='__main__')",1)
raise SystemExit(subprocess.call(cmd))
