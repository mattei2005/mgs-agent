#!/usr/bin/env bash
set -euo pipefail
export HERMES_HOME=/root/.hermes/profiles/ares
export HERMES_PROFILE=ares
exec /usr/bin/timeout --signal=TERM --kill-after=5s 165s /usr/bin/python3 -c '
import json,os,subprocess,sys
script="/root/.hermes/profiles/ares/scripts/shein-g004-mavroa07-cpr-roi-20261126.py"
cmd=json.loads(subprocess.check_output(["/root/.local/bin/hermes","--print-runtime-command"],text=True))
old="runpy.run_module(\x27hermes_cli.main\x27, run_name=\x27__main__\x27, alter_sys=True)"
assert cmd[-1].endswith(old)
cmd[-1]=cmd[-1][:-len(old)]+"sys.argv="+repr([script]+sys.argv[1:])+"; runpy.run_path("+repr(script)+", run_name=\x27__main__\x27)"
os.execv(cmd[0],cmd)
' "$@"
