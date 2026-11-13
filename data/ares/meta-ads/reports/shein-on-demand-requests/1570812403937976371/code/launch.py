import json,subprocess,sys
from pathlib import Path
adapter=str(Path(__file__).with_name('batch.py'))
args=sys.argv[1:]
argv=json.loads(subprocess.check_output(['/root/.local/bin/hermes','--print-runtime-command'],text=True))
expected="runpy.run_module('hermes_cli.main', run_name='__main__', alter_sys=True)"
assert isinstance(argv,list) and argv[-1].count(expected)==1
argv[-1]=argv[-1].replace(expected,f"sys.argv={[adapter,*args]!r}; runpy.run_path(sys.argv[0],run_name='__main__')",1)
raise SystemExit(subprocess.call(argv))
