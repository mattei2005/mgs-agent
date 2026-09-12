"""Run finance attribution browser acceptance with the owner credential only on stdin."""
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, '/root/mgs-agent/scripts')
from mgs_google_workspace_auth import load_env
load_env()
sys.path.insert(0, str(ROOT / 'deploy'))
from runcloud_ops import VAULT, op

phase = sys.argv[1] if len(sys.argv) > 1 else 'stage'
assert phase in {'stage', 'production'}
item = op(['item', 'get', 'MGS Finance - rodolfo - dash.mgsdigitalcorp.com', '--vault', VAULT, '--format', 'json', '--reveal'])
fields = {field.get('id'): field.get('value') for field in item['fields']}
assert fields['username'] == 'rodolfo' and fields['password']
process = subprocess.run(
    ['node', str(ROOT / 'tests/finance-attribution-browser.mjs'), phase],
    input=json.dumps({'username': fields['username'], 'password': fields['password']}),
    text=True,
    capture_output=True,
    timeout=240,
    cwd=ROOT,
)
print(process.stdout)
if process.stderr:
    print(process.stderr[-3000:])
raise SystemExit(process.returncode)
