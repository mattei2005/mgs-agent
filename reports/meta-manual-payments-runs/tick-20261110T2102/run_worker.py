import os,sys,json,shutil,subprocess
from pathlib import Path
B=Path(__file__).parent;R=Path(shutil.which('hermes')).resolve().parents[2];sys.path.insert(0,str(R))
from pm.environments import activate_dependencies
activate_dependencies(R)
S=Path('/root/.hermes/profiles/zeus/skills/ops/meta-manual-payments-planning/scripts')
name=sys.argv[1];args=sys.argv[2:]
r=subprocess.run([sys.executable,str(S/(name+'.py')),*args],capture_output=True,text=True,timeout=540)
for suffix,text in [('stdout',r.stdout),('stderr',r.stderr)]:
 p=B/(name+'-'+suffix+'.txt');p.write_text(text);p.chmod(0o600)
try: d=json.loads(r.stdout)
except Exception: print(json.dumps({'worker':name,'exit_code':r.returncode,'output_parse_error':True,'stdout_file':str(B/(name+'-stdout.txt'))}));raise SystemExit(2)
p=B/'phases.json';ph=json.loads(p.read_text())if p.exists()else{};ph[name]=d;p.write_text(json.dumps(ph,ensure_ascii=False,indent=2));p.chmod(0o600)
print(json.dumps({'worker':name,'exit_code':r.returncode,'result':d},ensure_ascii=False));raise SystemExit(r.returncode)
