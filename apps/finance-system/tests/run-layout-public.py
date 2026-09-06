"""Read-only public finance browser tests; credentials only in child stdin."""
import sys,pathlib,subprocess,json,os,argparse
ROOT=pathlib.Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--test',choices=['sync-browser.mjs','ui-browser.mjs','periods-browser.mjs'],required=True);args=p.parse_args()
sys.path.insert(0,'/root/mgs-agent/scripts');from mgs_google_workspace_auth import load_env
load_env();sys.path.insert(0,str(ROOT/'deploy'));from runcloud_ops import secret
password=secret('MGS Finance - rodolfo - dash.mgsdigitalcorp.com','password')
r=subprocess.run(['node','tests/'+args.test],input=json.dumps({'username':'rodolfo','password':password}),text=True,capture_output=True,cwd=ROOT,env={**os.environ,'FINANCE_PUBLIC':'1'},timeout=240)
print(r.stdout)
if r.returncode and not r.stdout:print(json.dumps({'pass':False,'stage':'runner','error':'test execution failed'}))
raise SystemExit(r.returncode)
