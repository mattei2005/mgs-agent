import json, subprocess, sys
argv=json.loads(subprocess.check_output(['/root/.local/bin/hermes','--print-runtime-command'],text=True))
expected="runpy.run_module('hermes_cli.main', run_name='__main__', alter_sys=True)"
assert argv[-1].count(expected)==1
adapter='/root/.hermes/profiles/ares/cache/scratch/shein-1568885727465447427/intraday.py'
argv[-1]=argv[-1].replace(expected,f"sys.argv=[{adapter!r},{sys.argv[1]!r}]; runpy.run_path(sys.argv[0],run_name='__main__')",1)
raise SystemExit(subprocess.call(argv))
