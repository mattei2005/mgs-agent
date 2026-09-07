"""Read-only authenticated public network browser acceptance, credentials in stdin only."""
import sys,pathlib,subprocess,json,os
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,'/root/mgs-agent/scripts');from mgs_google_workspace_auth import load_env
load_env();sys.path.insert(0,str(ROOT/'deploy'));from runcloud_ops import secret
password=secret('MGS Finance - rodolfo - dash.mgsdigitalcorp.com','password')
r=subprocess.run(['node','tests/network-browser.mjs'],input=json.dumps({'username':'rodolfo','password':password}),text=True,capture_output=True,cwd=ROOT,env={**os.environ,'FINANCE_PUBLIC':'1'},timeout=300)
print(r.stdout)
if r.returncode and not r.stdout:print(json.dumps({'pass':False,'stage':'runner','error':'test execution failed'}))
raise SystemExit(r.returncode)
