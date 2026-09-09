"""Run the scoped finance browser acceptance with canonical owner credentials on stdin only."""
import pathlib,sys,subprocess,json
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,'/root/mgs-agent/scripts')
from mgs_google_workspace_auth import load_env
load_env();sys.path.insert(0,str(ROOT/'deploy'))
from runcloud_ops import op,VAULT
item=op(['item','get','MGS Finance - rodolfo - dash.mgsdigitalcorp.com','--vault',VAULT,'--format','json','--reveal'])
fields={x.get('id'):x.get('value') for x in item['fields']};assert fields['username']=='rodolfo' and fields['password']
command=['node',str(ROOT/'tests/spend-placement-public.mjs')]
if '--candidate' in sys.argv:command.append('--candidate')
r=subprocess.run(command,input=json.dumps({'username':fields['username'],'password':fields['password']}),text=True,capture_output=True,timeout=190,cwd=ROOT)
print(r.stdout);print(r.stderr[-1800:]);raise SystemExit(r.returncode)
