"""Read existing 1Password logins, pass only through stdin, never print/persist credentials."""
from pathlib import Path
import sys,json,subprocess
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'deploy'))
from runcloud_ops import secret
sys.path.insert(0,'/root/mgs-agent/scripts');from mgs_google_workspace_auth import load_env
load_env();phase=sys.argv[1];assert phase in ['stage','production'];D=R/'private/history-ui-1546894693135028234';credentials={k:secret('MGS Finance - '+k+' - dash.mgsdigitalcorp.com','password') for k in ['rodolfo','nicolas','joe','isliago','kelly','icaro']}
with (D/(phase+'-browser.log')).open('w') as log:
 p=subprocess.run(['node','tests/history-ui-public.mjs',phase],cwd=R,input=json.dumps(credentials),text=True,stdout=log,stderr=subprocess.STDOUT,timeout=570)
print(json.dumps({'phase':phase,'exit_code':p.returncode,'evidence':str(D/(phase+'-browser.log'))}));sys.exit(p.returncode)
